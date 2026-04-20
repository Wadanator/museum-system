# TODO: Ambient Loop Mode (24/7 Auto-Start Scene)

## Čo chceme

Dva prevádzkové módy systému:

| Mód | Správanie |
|-----|-----------|
| **classic** (aktuálny) | Scéna sa spustí na stlačenie tlačidla, prebehne raz, skončí |
| **ambient** (nový) | Po štarte RPI sa scéna automaticky spustí a opakuje sa donekonečna, 24/7 |

Ambient mód je určený na situácie kde RPI hrá rolu „pozadového displeja" — video slučka, hudba na pozadí, striedanie zvukov — bez potreby interakcie návštevníka.

---

## Hodnotenie náročnosti

**Stredná. Väčšina logiky je už hotová.** Scéna sa spúšťa, beží, končí. Treba pridať:
1. Config kľúč na výber módu
2. Auto-start pri štarte systému
3. Loop-restart keď scéna skončí
4. Voliteľne: web dashboard indikátor módu

Žiadne zásahy do state machine, MQTT, ani audio/video handlerov nie sú potrebné.

---

## Config zmeny

### `raspberry_pi/config/config.ini.example`

Nová sekcia `[Startup]`:

```ini
[Startup]
# Mód spustenia: classic | ambient
mode = classic

# Ak mode = ambient: automaticky spustí túto scénu po štarte (názov súboru)
# Ak je prázdne, použije sa hodnota z [Json] json_file_name
ambient_scene =

# Pauza medzi opakovaním scény v sekundách (len v ambient móde)
loop_restart_delay = 2
```

---

## Súbory, ktoré by to zasiahlo

### 1. `raspberry_pi/utils/config_manager.py`
- Načítať nové kľúče: `startup_mode`, `ambient_scene`, `loop_restart_delay`
- Vrátiť ich cez `get_all_config()`

```python
# Cca čo pribudne:
config['startup_mode'] = parser.get('Startup', 'mode', fallback='classic')
config['ambient_scene'] = parser.get('Startup', 'ambient_scene', fallback='')
config['loop_restart_delay'] = parser.getfloat('Startup', 'loop_restart_delay', fallback=2.0)
```

---

### 2. `raspberry_pi/main.py` — `MuseumController`

**a) Auto-start po MQTT spojení:**

V metóde `run()`, za blokom MQTT spojenia:

```python
# Ak ambient mód → spusti scénu hneď po štarte
if self.config['startup_mode'] == 'ambient':
    scene = self.config.get('ambient_scene') or self.json_file_name
    self._initiate_scene_start(scene, "Ambient mode: auto-start on boot")
```

**b) Loop-restart keď scéna skončí:**

V metóde `_run_scene_logic()`, v bloku `finally`, pred `broadcast_stop()`:

```python
# Ak ambient mód a shutdown nebol vyžiadaný → reštartuj scénu
if self.config['startup_mode'] == 'ambient' and not self.shutdown_requested:
    time.sleep(self.config['loop_restart_delay'])
    self._initiate_scene_start(scene_filename, "Ambient loop: restarting scene")
    return  # nevolať broadcast_stop, scéna ide znovu
```

**c) Tlačidlo v ambient móde — dôležité rozlíšenie:**

Existujú dva typy "tlačidiel" v systéme a správajú sa rozdielne:

| Typ | Čo robí | Ambient mód |
|-----|---------|-------------|
| **GPIO štartovací button** (`button_handler.py`) | Spustí default scénu | **IGNOROVAŤ** |
| **MQTT `<room_id>/scene` + `START`** | → `button_callback()` → spustí default scénu | **IGNOROVAŤ** — rovnaký efekt ako GPIO |
| **MQTT `<room_id>/start_scene`** | → `named_scene_callback()` → spustí konkrétnu scénu | **IGNOROVAŤ** |
| **Akýkoľvek iný MQTT topic** (napr. `room1/button1`, custom správy) | → `scene_parser.register_mqtt_event()` → `mqttMessage` transition | **FUNGUJE normálne** |

Kľúčové: ignorovanie sa deje na úrovni `on_button_press()` a `start_scene_by_name()` v `MuseumController`. Routing v `mqtt_message_handler.py` sa nemení — správy na scene-start callbacky jednoducho nic neurobia, ostatné idú do scény ako doteraz.

Ignorovanie sa týka **iba** GPIO štartovacieho tlačidla:

```python
def on_button_press(self):
    if self.config['startup_mode'] == 'ambient':
        return  # ignoruj len GPIO start button, MQTT inputy fungujú normálne
    self._initiate_scene_start(self.json_file_name, "Button pressed")
```

---

### 3. `raspberry_pi/Web/routes/status.py`

Pridať `startup_mode` do status response, aby dashboard vedel v akom móde beží:

```python
'startup_mode': controller.config.get('startup_mode', 'classic'),
```

---

### 4. `raspberry_pi/Web/dashboard.py` — voliteľné

- Zobraziť badge „AMBIENT MODE" keď je aktívny
- Prípadne tlačidlo na manuálne zastavenie/reštart slučky cez web

---

### 5. `raspberry_pi/watchdog.py` — žiadna zmena potrebná

Watchdog číta `/tmp/museum_scene_state`. V ambient móde bude hodnota vždy `running` — watchdog teda nebude reštartovať službu, čo je správne správanie.

---

## Edge cases

| Situácia | Riešenie |
|----------|----------|
| Scéna sa nenájde pri loop-reštarte | Logovať error, čakať `loop_restart_delay`, skúsiť znovu |
| MQTT spadne počas ambient slučky | Existujúci reconnect v `mqtt_client.py` to rieši |
| Zmena `startup_mode` za behu | Reštart služby cez web dashboard alebo `sudo systemctl restart museum-system` |
| Ambient scéna je iná ako default scéna | Riešené cez `ambient_scene` config kľúč |
| Shutdown signal počas loop-restartu | `shutdown_requested` flag zastaví slučku pred ďalším štartom |

---

## Poradie implementácie

1. `config/config.ini.example` + `utils/config_manager.py` — načítanie nových kľúčov
2. `main.py` — auto-start logika v `run()`
3. `main.py` — loop-restart v `_run_scene_logic()` finally blok
4. `main.py` — ignorovanie tlačidla v ambient móde
5. `Web/routes/status.py` — expozícia módu v API
6. (voliteľné) Dashboard badge / toggle tlačidlo
