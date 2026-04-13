# Štruktúra JSON Scény

Tento dokument opisuje JSON kontrakt pre scény a runtime správanie v `raspberry_pi/utils/schema_validator.py`, `raspberry_pi/utils/state_machine.py`, `raspberry_pi/utils/state_executor.py`, `raspberry_pi/utils/transition_manager.py` a `raspberry_pi/utils/scene_parser.py`.

Scény sa načítavajú zo zložky `raspberry_pi/scenes/`.

---

## 1. Koreňová štruktúra

Schéma vyžaduje tieto polia na koreňovej úrovni:

* `sceneId` - povinné, string.
* `initialState` - povinné, string.
* `states` - povinné, objekt so stavmi scény.

Voliteľné polia:

* `version` - string.
* `description` - string.
* `globalEvents` - pole prechodov platných mimo aktuálneho stavu.

Schema na koreňovej úrovni nezakazuje ďalšie polia, ale validácia a runtime používajú práve vyššie uvedené položky.

Príklad:

```json
{
  "sceneId": "room1_intro",
  "version": "1.0",
  "description": "Ukážková scéna",
  "initialState": "START",
  "states": {
    "START": {
      "description": "Prvý stav"
    }
  }
}
```

---

## 2. Stav

Každý stav v `states` môže obsahovať iba tieto vlastnosti:

* `description`
* `onEnter`
* `onExit`
* `transitions`
* `timeline`

Objekty stavov majú `additionalProperties: false`, takže iné kľúče vnútri stavu validácia odmietne.

`initialState` musí existovať v `states`.

`goto` v prechodoch môže smerovať len do existujúceho stavu alebo na špeciálnu hodnotu `END`.

---

## 3. Akcie

Akcie sa používajú v `onEnter`, `onExit` a v `timeline`.

Povinné pole:

* `action` - `mqtt`, `audio` alebo `video`.

Polia podľa typu:

* `mqtt` - používa `topic` a `message`.
* `audio` - používa `message`.
* `video` - používa `message`.

Schema povoľuje aj `retain`, ale aktuálny `StateExecutor` publikuje MQTT akcie vždy s `retain=False`.

Príklad:

```json
{
  "action": "mqtt",
  "topic": "room1/light/1",
  "message": "ON"
}
```

---

## 4. Timeline

`timeline` je zoznam časovaných akcií, ktoré sa plánujú pri vstupe do stavu.

Každá položka musí mať:

* `at` - čas v sekundách od vstupu do stavu.

Položka môže obsahovať:

* jednu akciu cez `action`, `topic`, `message`
* alebo pole akcií cez `actions`

Runtime ich nespúšťa v hlavnom ticku. `StateExecutor` ich pri vstupe do stavu naplánuje cez `threading.Timer`.

`check_and_execute_timeline()` zostáva v kóde iba kvôli kompatibilite a nerobí nič.

Príklady:

```json
{
  "at": 5,
  "action": "audio",
  "message": "PLAY:sfx_uvod_rec.mp3:1.0"
}
```

```json
{
  "at": 10,
  "actions": [
    {
      "action": "mqtt",
      "topic": "room1/light/1",
      "message": "ON"
    }
  ]
}
```

---

## 5. Prechody

Prechody sa používajú v `transitions` aj v `globalEvents`.

Povinné polia:

* `type`
* `goto`

Runtime spracúva tieto typy prechodov:

* `timeout`
* `audioEnd`
* `videoEnd`
* `mqttMessage`
* `always`

Voliteľné polia podľa typu:

* `delay` - používa sa pri `timeout`.
* `target` - používa sa pri `audioEnd` a `videoEnd`.
* `topic` - používa sa pri `mqttMessage`.
* `message` - používa sa pri `mqttMessage`.

`mqttMessage` porovnáva topic aj payload presne, bez wildcardov a bez čiastočnej zhody.

`TransitionManager.check_transitions()` prechádza zoznam prechodov v poradí, v akom sú zapísané v JSON-e, a vráti prvý prechod, ktorý sa splní.

`timeout` pracuje s časom stráveným v aktuálnom stave.

`audioEnd` a `videoEnd` fungujú len vtedy, keď handler cez callback zaregistruje presný názov skončeného súboru do príslušnej fronty.

`always` sa vyhodnotí bez podmienky a v runtime nevyužíva `delay`.

Príklad:

```json
{
  "type": "mqttMessage",
  "topic": "room1/button1",
  "message": "PRESSED",
  "goto": "activated"
}
```

Špeciálna hodnota `END` ukončí scénu. Ak stav s názvom `END` existuje, `StateMachine` ho vie vrátiť cez `get_current_state_data()`.

---

## 6. Runtime správanie

### Načítanie scény

`SceneParser.load_scene()` deleguje na `StateMachine.load_scene()`.

`StateMachine.load_scene()`:

* načíta JSON súbor,
* overí schému cez `validate_scene_json()`,
* skontroluje, či `initialState` existuje,
* skontroluje, či všetky `goto` cieľe v `transitions` a `globalEvents` existujú alebo sú `END`,
* uloží plnú scénu aj do `scene_data`.

### Spustenie scény

`SceneParser.start_scene()`:

* odmietne štart, ak nebola načítaná scéna,
* pri prítomnom `audio_handler` prehľadá celú scénu a vyzbiera všetky audio súbory z akcií typu `audio`,
* pošle ich do `preload_files_for_scene()`,
* vymaže pending eventy a timeline tracking,
* spustí `StateMachine.start()`,
* po vstupe do počiatočného stavu vykoná jeho `onEnter` akcie.

Audio preloading rozpoznáva aj formát `PLAY:<subor>:<volume>` a berie z neho názov súboru.

### Spracovanie ticku

`SceneParser.process_scene()` v každom ticku:

* zavolá `audio_handler.check_if_ended()` a `video_handler.check_if_ended()` ak existujú,
* ukončí spracovanie, ak je scéna v stave `END`,
* prečíta `globalEvents` a vyhodnotí ich podľa celkového času scény,
* vykoná timeline akcie pre aktuálny stav,
* vyhodnotí state-level `transitions` podľa času v stave.

`globalEvents` sa vyhodnocujú pred timeline a pred lokálnymi prechodmi.

Pre `globalEvents` sa používa čas od štartu celej scény, nie čas od vstupu do aktuálneho stavu.

### Zmena stavu

Pri zmene stavu `SceneParser`:

* vykoná `onExit` pôvodného stavu,
* zavolá `goto_state()` na `StateMachine`,
* vymaže pending eventy v `TransitionManager`,
* vynuluje timeline tracking,
* vykoná `onEnter` nového stavu.

`StateMachine` si zároveň drží históriu stavov, najviac 200 položiek.

Po každej zmene stavu sa v `TransitionManager` vymažú všetky čakajúce MQTT, audio aj video eventy, takže nový stav nezačne s udalosťami zdedenými zo starého stavu.

### Zastavenie scény

`SceneParser.stop_scene()`:

* zastaví všetko audio,
* resetuje runtime stav machine,
* nastaví aktuálny stav na `END`,
* vymaže eventy,
* resetuje timeline tracking.

---

## 7. TransitionManager

`TransitionManager` spravuje tri fronty udalostí:

* MQTT eventy
* audio end eventy
* video end eventy

Fronty majú maximálnu veľkosť 50 položiek.

Prechody sa vyhodnocujú v poradí, v akom sú v poli zapísané. Prvý prechod, ktorý sa splní, vráti cieľový stav.

`timeout` používa porovnanie `state_elapsed_time >= delay`.

`audioEnd` a `videoEnd` sú spustené po zachytení konca konkrétneho súboru.

`always` sa vykoná okamžite bez podmienky.

MQTT eventy sa do fronty ukladajú ako dvojica `topic` a `message` a z fronty sa po úspešnom zásahu odstránia. To isté platí pre audio a video end eventy.

`clear_events()` vyprázdni všetky tri fronty naraz a používa sa pri štarte scény aj pri každej zmene stavu.

---

## 8. Krátke zhrnutie

Ak chceš presne odlíšiť správanie scény podľa kódu, stačí držať tieto pravidlá:

* validácia prejde len pre schému zo `schema_validator.py`
* prechody musia smerovať do existujúceho stavu alebo na `END`
* timeline sa plánuje pri vstupe do stavu cez `threading.Timer`
* `mqttMessage` porovnáva presný topic aj payload
* `globalEvents` sú vyhodnocované pred lokálnymi prechodmi
* `check_and_execute_timeline()` je iba kompatibilitný hook a nerobí nič
