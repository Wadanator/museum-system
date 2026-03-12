# Diagram Generation Guide

Univerzálny toolkit na generovanie SVG diagramov cez Graphviz + Python.
Candy/highlighter paleta — čitateľné na obrazovke, tlačí sa čisto aj v greyscale.

---

## Ako pracovať s týmto guide

AI dostane vždy konkrétne súbory (`theme.py`, `_template_flowchart.py`, `_template_block.py`, atď.).
Tento MD slúži ako **pravidlá a orientácia** — nie ako náhrada za tie súbory.

**Prísne pravidlá pre AI:**
- Použi **iba** to čo je v priložených súboroch — žiadne predpoklady, žiadne vymýšľanie
- Ak niečo chýba (token, trieda, helper) → **ozvi sa**, nepokračuj s odhadom
- Farby a štýly **výhradne** cez tokeny z `theme.py` — nikdy natvrdo
- Uzly a hrany **výhradne** cez štýly z `theme.py` — nikdy vlastné atribúty

---

## Základný princíp

Každý diagram = **jeden súbor = jedna myšlienka.**

```
Čo chcem zobraziť?
    → Vyber triedu z theme.py
        → Nový .py súbor (skopíruj šablónu)
            → render_diagram(dot)
```

---

## Súborová štruktúra

```
museum_diagrams/
├── theme.py                 ← farby, tvary, štýly  (NEMENIŤ bez dôvodu)
├── gv_html.py               ← HTML-label helpery (pre blokové diagramy)
├── render.py                ← export do SVG, auto-názov podľa skriptu
│
├── _template_flowchart.py   ← šablóna pre Flowchart / Pipeline / Architecture / SM / SW
├── _template_block.py       ← šablóna pre HTML-label blok (SceneAnatomy / StateAnatomy)
│
├── scene_json.py            ← Scene JSON štruktúra  (HTML-label blok)
├── state_anatomy.py         ← State štruktúra       (HTML-label blok)
├── mqtt_flow.py             ← MQTT flow             (Flowchart)
│
└── outputs/                 ← všetky vygenerované SVG
```

---

## Ktorú triedu použiť?

| Chcem zobraziť | Trieda |
|---|---|
| Algoritmus, tok udalostí, "čo sa deje keď X" | `Flowchart` |
| Prechody medzi stavmi (JSON state machine, UI) | `StateMachine` |
| Fyzická topológia, HW zariadenia, protokoly | `Architecture` |
| Štruktúra kódu — triedy, moduly, volania | `Software` |
| Tok dát / médií / správ, pipeline, fronty | `Pipeline` |
| Vnorená JSON / config schéma (uzly + hrany) | `JSON` |
| Referenčný blok: Scene objekt | `SceneAnatomy` |
| Referenčný blok: State objekt | `StateAnatomy` |

Konkrétne uzly, hrany a atribúty každej triedy → čítaj priamo z `theme.py`.

---

## Šablóny — rýchly štart

| Šablóna | Použitie |
|---|---|
| `_template_flowchart.py` | Flowchart, Pipeline, Architecture, StateMachine, Software |
| `_template_block.py` | HTML-label blok — SceneAnatomy alebo StateAnatomy |
Tu kĽudne môžeš pridať navyše šablonu ak to považuješ za dobré... ale musiš vždy updatenut tento md subor..

**Postup:**
1. Skopíruj šablónu, premenuj (napr. `mqtt_routing.py`)
2. Zmeň triedu v `from theme import X` podľa tabuľky vyššie
3. Nahraď uzly a hrany — **nikdy nemeň `**X.XXX` štýly, len labely**
4. `python3 nazov.py` → `outputs/nazov.svg`

---

## Pravidlá obsahu — čo patrí na diagram

### Menej textu = lepší diagram
- Každý uzol/pole má **maximálne 2–3 slová** — názov, nie vysvetlenie
- Žiadne vety, žiadne popisy — na to je BP text okolo obrázka
- Ak sa obsah na diagram nezmestí bez skracovania → rozdeliť na viac obrázkov

### Lievik informácií (pre komplexné témy)
Ak téma obsahuje viac vrstiev, rozdeľ ju do série diagramov od povrchu do hĺbky:

```
Diagram 1 — celok / prehľad       (čo to je, hlavné časti, väzby)
Diagram 2 — jedna časť do hĺbky
Diagram 3 — ďalšia časť
```

Každý obrázok má byť pochopiteľný sám o sebe.

### Pred generovaním — opýtaj sa
Keď dostaneš zadanie na diagram komplexnejšej témy:
1. **Navrhni štruktúru** — koľko obrázkov, čo každý zobrazuje
2. **Počkaj na potvrdenie** — až potom začni generovať
3. Jednoduchá vec (jeden uzol, jeden tok) → generuj priamo bez pýtania

---

## Farebná logika — rýchly prehľad

```
🟢 MINT       → aktívny, vstup, zdroj
🔵 SKY BLUE   → logika, detail, podproces
🟣 LAVENDER   → sekvencia, čas, interface
🍑 PEACH      → I/O, komunikácia, výstup
🟡 LEMON      → rozhodnutie, fronta, pozornosť
🌸 ROSE       → error, externý impulz, koniec
⬜ NEUTRAL    → vonkajší systém
```

Platí konzistentne naprieč všetkými triedami. Presné hex hodnoty → `theme.py`.

---

## Stav diagramov — zhoda s kódom

| Súbor | Stav | Poznámka |
|---|---|---|
| `scene_json.py` | ✅ Sedí | Polia zodpovedajú `SCENE_SCHEMA` v `schema_validator.py` |
| `state_anatomy.py` | ✅ Sedí | Všetkých 5 transition typov: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always` |


### Menej textu = lepší diagram
- Každý uzol/pole má **maximálne 2–3 slová** — názov, nie vysvetlenie
- Žiadne vety, žiadne popisy — na to je BP text okolo obrázka
- Ak sa na diagram nezmestí bez skracovania → rozdeliť na viac obrázkov

### Lievik informácií (pre komplexné témy)
Ak téma obsahuje viac vrstiev (napr. štruktúra JSON, architektúra systému),
rozdeľ ju do série diagramov od povrchu do hĺbky:

```
Diagram 1 — celok / prehľad       (čo to je, hlavné časti, väzby)
Diagram 2 — jedna časť do hĺbky   (napr. konkrétna sekcia JSON)
Diagram 3 — ďalšia časť            (napr. transitions, timeline…)
```

Každý obrázok má byť pochopiteľný sám o sebe, bez čítania ostatných.

### Pred generovaním — opýtaj sa
Keď dostaneš zadanie na diagram komplexnejšej témy:
1. **Navrhni štruktúru** — koľko obrázkov, čo každý zobrazuje
2. **Počkaj na potvrdenie** — až potom začni generovať
3. Jednoduchá vec (jeden uzol, jeden tok) → generuj priamo bez pýtania

Príklady kedy sa opýtať:
- "Nakresli štruktúru XY" kde XY má viac podsystémov
- "Zdokumentuj ako funguje Z" kde Z má viac fáz/vrstiev
- Akékoľvek zadanie kde cítiš že jeden obrázok nestačí

---

## Súborová štruktúra

```
museum_diagrams/
├── theme.py                 ← farby, tvary, štýly  (NEMENIŤ bez dôvodu)
├── gv_html.py               ← HTML-label helpery (pre blokové diagramy)
├── render.py                ← export do SVG, auto-názov podľa skriptu
│
├── _template_flowchart.py   ← šablóna pre Flowchart / Pipeline / Architecture / SM / SW
├── _template_block.py       ← šablóna pre HTML-label blok (SceneAnatomy / StateAnatomy)
│
├── scene_json.py            ← Scene JSON štruktúra  (HTML-label blok)
├── state_anatomy.py         ← State štruktúra       (HTML-label blok)
├── mqtt_flow.py             ← MQTT flow             (Flowchart)
│
└── outputs/                 ← všetky vygenerované SVG
```

---

## Ktorú triedu použiť?

| Chcem zobraziť | Trieda | Typické uzly |
|---|---|---|
| Algoritmus, tok udalostí, "čo sa deje keď X" | `Flowchart` | TERMINAL, PROCESS, DECISION, IO, SUBPROCESS, EVENT |
| Prechody medzi stavmi (JSON state machine, UI) | `StateMachine` | INITIAL, NORMAL, ACTIVE, END |
| Fyzická topológia, HW zariadenia, protokoly | `Architecture` | MASTER, DEVICE, BROKER, DASHBOARD, SERVICE, EXTERNAL |
| Štruktúra kódu — triedy, moduly, volania | `Software` | CLASS, INTERFACE, MODULE, FUNCTION, DATABASE |
| Tok dát / médií / správ, pipeline, fronty | `Pipeline` | SOURCE, PROCESS, QUEUE, SINK, SERVICE, STORE, ERROR |
| Vnorená JSON / config schéma (uzly + hrany) | `JSON` | ROOT, OBJECT, ARRAY, VALUE |
| Referenčný blok: Scene objekt | `SceneAnatomy` | HTML-label, jeden uzol |
| Referenčný blok: State objekt | `StateAnatomy` | HTML-label, jeden uzol |

---

## Šablóny — rýchly štart

Namiesto písania od nuly skopíruj príslušnú šablónu:

| Šablóna | Použitie |
|---|---|
| `_template_flowchart.py` | Flowchart, Pipeline, Architecture, StateMachine, Software |
| `_template_block.py` | HTML-label blok — SceneAnatomy alebo StateAnatomy |

**Postup:**
1. Skopíruj šablónu, premenuj (napr. `mqtt_routing.py`)
2. Zmeň triedu v `from theme import X` podľa tabuľky vyššie
3. Nahraď uzly a hrany — **nikdy nemeň `**X.XXX` štýly, len labely**
4. `python3 nazov.py` → `outputs/nazov.svg`

---

## Šablóna — každý nový diagram

```python
"""
nazov_diagramu.py
-----------------
Jedna veta čo tento diagram ukazuje.
Output: outputs/nazov_diagramu.svg
"""

import graphviz
from theme import NazovTriedy as X   # napr. Flowchart, Pipeline, Software...
from render import render_diagram

dot = graphviz.Digraph(name="nazov_diagramu")
dot.attr("graph", **{k: v for k, v in X.GRAPH.items()})

# --- uzly ---
dot.node("id", "Label",  **X.TYP_UZLA)

# --- hrany ---
dot.edge("a", "b", **X.TYP_HRANY)
dot.edge("a", "c", label="  podmienka", **X.BRANCH)

render_diagram(dot)

if __name__ == "__main__":
    # spusti priamo: python3 nazov_diagramu.py
    pass
```

---

## Triedy a ich uzly / hrany

### `Flowchart` — algoritmy, event flow
```
Uzly:    TERMINAL · PROCESS · DECISION · IO · SUBPROCESS · EVENT · NOTE
Hrany:   FLOW · BRANCH · DASHED
Graph:   F.GRAPH  (rankdir TB, splines ortho)
```
Vzor — "čo sa stane keď príde MQTT správa":
```python
from theme import Flowchart as F

dot.node("start",  "Príde správa",     **F.TERMINAL)
dot.node("parse",  "Parsuj topic",      **F.PROCESS)
dot.node("check",  "Matchuje state?",   **F.DECISION)
dot.node("ignore", "Ignoruj",           **F.IO)
dot.node("exec",   "Vykonaj akciu",     **F.SUBPROCESS)
dot.node("end",    "Hotovo",            **F.TERMINAL)

dot.edge("start",  "parse",   **F.FLOW)
dot.edge("parse",  "check",   **F.FLOW)
dot.edge("check",  "exec",    label="  áno", **F.BRANCH)
dot.edge("check",  "ignore",  label="  nie", **F.BRANCH)
dot.edge("exec",   "end",     **F.FLOW)
```

---

### `Architecture` — fyzická topológia, protokoly
```
Uzly:    MASTER · DEVICE · BROKER · DASHBOARD · SERVICE · EXTERNAL · MODULE
Hrany:   MQTT · MQTT_LABELLED · SOCKET_IO · HTTP · LINK · WIRE
Graph:   Arch.GRAPH  (nodesep 0.8, ranksep 1.0)
```
Vzor — RPI ↔ ESP32 cez MQTT:
```python
from theme import Architecture as Arch

dot.node("rpi",    "Raspberry Pi",   **Arch.MASTER)
dot.node("broker", "Mosquitto",      **Arch.BROKER)
dot.node("esp1",   "ESP32 svetlá",   **Arch.DEVICE)
dot.node("esp2",   "ESP32 motor",    **Arch.DEVICE)
dot.node("dash",   "Dashboard",      **Arch.DASHBOARD)
dot.node("vlc",    "vlc.service",    **Arch.SERVICE)

dot.edge("rpi",   "broker", **Arch.MQTT)
dot.edge("esp1",  "broker", label="sensor/light", **Arch.MQTT_LABELLED)
dot.edge("broker","esp2",   label="motor/cmd",    **Arch.MQTT_LABELLED)
dot.edge("rpi",   "vlc",    **Arch.WIRE)
dot.edge("rpi",   "dash",   **Arch.SOCKET_IO)
```

---

### `Software` — štruktúra kódu
```
Uzly:    CLASS · ABSTRACT · INTERFACE · MODULE · FUNCTION · DATABASE · CONSTANT · EXTERNAL
Hrany:   INHERITS · IMPLEMENTS · USES · CALLS · OWNS
Graph:   SW.GRAPH  (splines ortho)
```
Vzor — vnútorná štruktúra RPI kódu:
```python
from theme import Software as SW

dot.node("app",       "app.py",           **SW.MODULE)
dot.node("sm",        "StateMachine",     **SW.CLASS)
dot.node("player",    "VideoPlayer",      **SW.CLASS)
dot.node("mqtt",      "MQTTClient",       **SW.CLASS)
dot.node("iface",     "IActionHandler",   **SW.INTERFACE)
dot.node("scenes_db", "scenes/*.json",    **SW.DATABASE)
dot.node("vlc",       "python-vlc",       **SW.EXTERNAL)

dot.edge("app",    "sm",      **SW.OWNS)
dot.edge("app",    "mqtt",    **SW.OWNS)
dot.edge("sm",     "player",  **SW.CALLS)
dot.edge("player", "iface",   **SW.IMPLEMENTS)
dot.edge("player", "vlc",     **SW.USES)
dot.edge("sm",     "scenes_db", **SW.USES)
```

---

### `Pipeline` — tok dát, správ, médií
```
Uzly:    SOURCE · PROCESS · QUEUE · SINK · SERVICE · STORE · ERROR
Hrany:   FLOW · ASYNC · PUBLISH · SUBSCRIBE · ERROR_EDGE
Graph:   PL.GRAPH  (ranksep 0.9)
```
Vzor — video playback pipeline na RPI:
```python
from theme import Pipeline as PL

dot.node("trigger", "MQTT: play_video",  **PL.SOURCE)
dot.node("sm",      "StateMachine",      **PL.PROCESS)
dot.node("queue",   "ActionQueue",       **PL.QUEUE)
dot.node("player",  "VideoPlayer",       **PL.SERVICE)
dot.node("vlc",     "libVLC",            **PL.PROCESS)
dot.node("screen",  "HDMI výstup",       **PL.SINK)
dot.node("log",     "event.log",         **PL.STORE)
dot.node("err",     "ErrorHandler",      **PL.ERROR)

dot.edge("trigger", "sm",     **PL.FLOW)
dot.edge("sm",      "queue",  **PL.PUBLISH)
dot.edge("queue",   "player", **PL.SUBSCRIBE)
dot.edge("player",  "vlc",    **PL.FLOW)
dot.edge("vlc",     "screen", **PL.FLOW)
dot.edge("player",  "log",    **PL.ASYNC)
dot.edge("vlc",     "err",    **PL.ERROR_EDGE)
```

---

### `StateMachine` — stavové prechody
```
Uzly:    INITIAL · NORMAL · ACTIVE · END
Hrany:   TRANSITION · TRANSITION_TIMEOUT · SELF_LOOP
Graph:   SM.GRAPH
```
```python
from theme import StateMachine as SM

dot.node("init",  "",        **SM.INITIAL)
dot.node("idle",  "IDLE",    **SM.NORMAL)
dot.node("play",  "PLAYING", **SM.ACTIVE)   # aktuálny stav
dot.node("end",   "",        **SM.END)

dot.edge("init", "idle", **SM.TRANSITION)
dot.edge("idle", "play", label="play_video",  **SM.TRANSITION)
dot.edge("play", "idle", label="video_end",   **SM.TRANSITION)
dot.edge("play", "end",  label="timeout(60)", **SM.TRANSITION_TIMEOUT)
```

---

## Farebnú logika — rýchly cheat-sheet

```
🟢 MINT       → aktívny, vstup, zdroj, "život začína"
🔵 SKY BLUE   → logika, detail, podproces, child-level
🟣 LAVENDER   → sekvencia, čas, interface, "kontrakt"
🍑 PEACH      → I/O, komunikácia, výstup, "tok von"
🟡 LEMON      → rozhodnutie, pozornosť, fronta (čaká)
🌸 ROSE       → externý impulz, error, koniec, udalosť
⬜ NEUTRAL    → vonkajší systém, neznámy komponent
```

Toto platí konzistentne naprieč **všetkými** triedami — ak vidíš lemon,
vieš že ide o rozhodnutie alebo frontu. Ak vidíš rose, ide o error alebo
externý impulz.

---

## HTML-label blokové diagramy (gv_html.py)

Pre **referenčné / cheat-sheet diagramy** kde chceš jeden veľký
annotovaný blok (napr. `scene_json.py`, `state_anatomy.py`).

```python
from theme import SceneAnatomy as A   # alebo StateAnatomy
from gv_html import font, thin_rule, section_column, action_block, ...

dot.attr("graph", **{k: v for k, v in A.GRAPH.items()})
dot.node("root", label=build_label(), **A.NODE)
```

### Dostupné helpery

| Funkcia | Použitie |
|---|---|
| `font(text, size, color, bold, italic)` | `<FONT>` tag |
| `thin_rule(colspan, color)` | 1px horizontálny oddeľovač |
| `spacer(colspan, height)` | prázdny riadok |
| `action_block(type, fields)` | blok akcie (mqtt / audio / video) |
| `timeline_block(at, type, fields)` | položka timeline |
| `section_column(header, *items)` | stĺpec so záhlavím |
| `transition_card(type, fields)` | karta prechodu |

### Tokeny SceneAnatomy (mint — parent)

| Token | Popis |
|---|---|
| `BG_STATE / BG_HEADER` | celkové bg / titulná lišta (mint) |
| `SUB_GLOBAL_HDR/BG/BDR` | globalEvents subsekcia (teal) |
| `SUB_STATES_HDR/BG/BDR` | states subsekcia (sky — naznačuje child) |

### Tokeny StateAnatomy (sky blue — child)

| Token | Popis |
|---|---|
| `BG_STATE / BG_HEADER` | celkové bg / titulná lišta (sky) |
| `SEC_ONENTER` | `(header, bg, border, divider)` — mint |
| `SEC_TIMELINE` | `(header, bg, border, divider)` — lavender |
| `SEC_ONEXIT` | `(header, bg, border, divider)` — peach |
| `SEC_TRANS_HDR/BG/BDR` | transitions sekcia — lemon |
| `ACT_MQTT / ACT_AUDIO / ACT_VIDEO` | farba typu akcie |
| `TR_TIMEOUT / TR_MQTT / TR_VIDEO / TR_ALWAYS` | farba typu prechodu |

---

## Stav diagramov — zhoda s kódom

| Súbor | Stav | Poznámka |
|---|---|---|
| `scene_json.py` | ✅ Sedí | Polia zodpovedajú `SCENE_SCHEMA` v `schema_validator.py` |
| `state_anatomy.py` | ✅ Sedí | Všetkých 5 transition typov: `timeout`, `audioEnd`, `videoEnd`, `mqttMessage`, `always` |

---

## Pravidlá

```
- Jeden súbor = jeden diagram = jedna myšlienka
- Importuj z theme.py, gv_html.py, render.py — nepíš znova to čo tam je
- Farby NIKDY natvrdo — len tokeny z theme.py
- Vyber správnu triedu podľa tabuľky vyššie — netlač všetko do Flowchart
- render_diagram(dot) na konci, bez argumentov
- Názov súboru = názov SVG výstupu
```


Ak si pochopil obsah tohoto súboru tak daj vedieť že si si všetko podrobne naštudoval.