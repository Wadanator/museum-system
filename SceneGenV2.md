# SceneGen V2 — Špecifikácia Vizuálneho Editora Scén

> **Stav:** Návrh (neprogramovať, len plánovanie)  
> **Dátum:** 2025-05-16  
> **Cieľ:** Nahradiť aktuálny standalone SceneGen plnohodnotným vizuálnym editorom priamo v `museum-dashboard`, s FL Studio-štýl timeline pre každý stav.

---

## 1. Kontext a motivácia

### Kde sme dnes

**Standalone `SceneGen/`** je oddelená React/Tailwind appka:
- Edituje stavy (onEnter, timeline, onExit, transitions) cez formulárové inputy
- Timeline editor je iba textový zoznam riadkov `{ at: 1.4, action, topic, message }`
- Zariadenia sú hardcoded v `constants.js` (MQTT_DEVICES) — nie sú napojené na skutočné `devices.json` na Pi
- Žiadne napojenie na backend — export iba cez lokálne stiahnutie JSON

**`museum-dashboard/`** má:
- `SceneEditorModal` = Monaco JSON editor + `SceneVisualizer` (ReactFlow read-only graf)
- `api.getDevices()`, `api.getMedia('audio')`, `api.saveScene()` — všetky potrebné API volania existujú
- `useDevices`, `useMedia`, `useScenes` hooks — fungujúce
- Design system: `theme.css` s CSS premennými, komponenty `Button`, `Card`, `Modal`, `PageHeader`, `StatusBadge`
- `reactflow` nainštalovaný a použitý
- `react-hot-toast`, `lucide-react`, `@monaco-editor/react` nainštalované

### Kde chceme byť

SceneGenV2 = nový **View v museum-dashboard** (`SceneEditorView`), ktorý:
1. Nahrádza aktuálny `SceneEditorModal` ako plnohodnotný editor (nie modal)
2. Má FL Studio-štýl vizuálnu timeline pre každý stav
3. Je napojený na živé `devices.json` a `audio/` knižnicu z Pi
4. Ukladá scény priamo cez `api.saveScene()` na backend
5. Dodržiava 100% kompatibilitu so schémou `scene_schema` (validovanou cez `schema_validator.py`)

---

## 2. 100% Kompatibilita so Schémou

Schéma (`utils/schema_validator.py`) je zákon. SceneGenV2 musí generovať iba platné JSON:

```
Scene {
  sceneId: string
  description?: string
  version?: string
  initialState: string
  globalEvents?: Transition[]
  states: { [stateName: string]: State }
}

State {
  description?: string
  onEnter?: Action[]
  onExit?: Action[]
  timeline?: TimelineItem[]
  transitions?: Transition[]
}

Action {
  action: 'mqtt' | 'audio' | 'video'
  topic?: string
  message?: string | number | boolean
  retain?: boolean
}

TimelineItem {
  at: number          <- cas v sekundach od vstupu do stavu
  action: 'mqtt' | 'audio' | 'video'
  topic?: string
  message?: string | number | boolean
  -- ALEBO --
  actions?: Action[]  <- viacero akcii v jednom casovom bode
}

Transition {
  type: 'timeout' | 'mqttMessage' | 'audioEnd' | 'videoEnd' | 'always'
  goto: string
  delay?: number      <- len pre timeout
  topic?: string      <- len pre mqttMessage
  message?: string    <- len pre mqttMessage
  target?: string     <- len pre audioEnd/videoEnd
}
```

**Klucova pointa**: Timeline polozky su **bod v case** (`at: 1.4`), nie intervaly. Clip na vizualnej timeline predstavuje moment, nie trvanie. Vizualna sirka clipa je fixna (ikona + label), nie mapovanie na trvanie.

---

## 3. Integrácia do museum-dashboard

### Prečo nie standalone

Standalone SceneGen nemôže vedieť, aké zariadenia sú nakonfigurované v `devices.json` a aké audio súbory sú nahrané. Toto je blocker pre akýkoľvek zmysluplný editor — bez týchto dát by používateľ stále musel ručne písať topic stringy.

### Umiestnenie

```
museum-dashboard/src/
├── components/
│   └── SceneEditor/           <- nova domenova domena
│       ├── SceneEditorView.jsx        <- hlavny View (nahradzuje SceneEditorModal)
│       ├── StateList.jsx              <- lavy sidebar (zoznam stavov)
│       ├── StatePanel.jsx             <- prava plocha (editor / timeline)
│       ├── StateMetaForm.jsx          <- meno + popis stavu
│       ├── ActionListEditor.jsx       <- onEnter / onExit zoznam akcii
│       ├── TransitionEditor.jsx       <- editor prechodov
│       ├── VisualTimeline/
│       │   ├── VisualTimeline.jsx     <- FL Studio canvas
│       │   ├── TimelineTrack.jsx      <- jedna horizontalna stopa
│       │   ├── TimelineClip.jsx       <- jeden klik/bod na stope
│       │   ├── TimeRuler.jsx          <- pravitko v sekundach
│       │   └── TimelineToolbar.jsx    <- zoom, snap, trvanie osi
│       ├── Palette/
│       │   ├── ActionPalette.jsx      <- pravy panel s dostupnymi akciami
│       │   ├── DevicePalette.jsx      <- zariadenia z devices.json
│       │   └── AudioPalette.jsx       <- audio subory z /api/media/audio
│       └── GlobalEventsEditor.jsx     <- existujuca logika z SceneGen
├── hooks/
│   ├── useSceneEditor.js      <- centralny state management editora
│   ├── useTimeline.js         <- timeline drag logika (pointer events)
│   └── useDevicePalette.js    <- devices + audio nacitanie a formatovanie
├── styles/
│   └── views/
│       └── scene-editor-v2.css        <- view-specific styly
└── services/
    └── api.js                 <- EXISTUJUCE (api.getDevices, api.getMedia, api.saveScene)
```

### Navigácia

Nová položka v `Sidebar.jsx` dashboardu: **"Editor Scén"** → `/scene-editor` alebo ako modal s full-screen layout (preferovaný).

Alternatíva: upgrade `SceneEditorModal` na full-page view (otvára sa cez `navigate('/scene-editor/:sceneName')`).

---

## 4. Celkový UI Layout

```
+--------------------------------------------------------------------+
| HEADER: Nazov sceny | [Import] [Export JSON] [Ulozit na Pi] [X]   |
+---------------+-------------------------------------+---------------+
|               |                                     |               |
|  STATE LIST   |     HLAVNY EDITOR PANEL             |  PALETA       |
|  (sidebar)    |                                     |  (pravy panel)|
|               |  [STATE METADATA]                   |               |
|  INIT_ATMO    |  Nazov: INIT_ATMOSFERA              |  ZARIADENIA   |
|  > START_OH.  |  Popis: Uvod, atmosfera...          |  motor1       |
|  > ZVUK_ALA   |                                     |  motor2       |
|  > ZVUK_PARA  |  +-- ON ENTER ------------------+  |  light/fire   |
|  > ...        |  | [+] audio STOP              |   |  light/1..5   |
|               |  | [+] video STOP_VIDEO        |   |  effect/smoke |
|  [+ Novy]     |  | [+] audio PLAY:atmosfera... |   |  power/smoke  |
|               |  +---------------------------------+ |               |
|  GLOBAL       |                                     |  AUDIO SUBORY |
|  EVENTS       |  +-- VISUAL TIMELINE ------------+  |  atmosfera.wav|
|  [2 eventy]   |  | 0s  2s  4s  6s  8s  10s     |  |  sfx_para.wav |
|               |  | --+---------------------------  |  sfx_alarm..  |
|               |  |M  |[light/fire ON] [smoke ON] |  |  ...          |
|               |  |Q  |                           |  |               |
|               |  |T  |                           |  |  VIDEO SUBORY |
|               |  |T  |                           |  |  intro.mp4    |
|               |  +--+---------------------------  |  |  ...          |
|               |  |AU |[atmosfera.wav 0.5vol]     |  |               |
|               |  +--+---------------------------  |  |               |
|               |  |VI |[STOP_VIDEO]               |  |               |
|               |  +-------------------------------+  |               |
|               |                                     |               |
|               |  +-- ON EXIT ----------------+      |               |
|               |  +----------------------------+     |               |
|               |                                     |               |
|               |  +-- TRANSITIONS ------------+      |               |
|               |  | timer 10s -> START_OHEN   |      |               |
|               |  +----------------------------+     |               |
+---------------+-------------------------------------+---------------+
| BOTTOM TABS: [Editor] [Flow Graf] [JSON Preview]                   |
+--------------------------------------------------------------------+
```

---

## 5. Panel 1: State List (ľavý sidebar)

### Čo zobrazuje
- Zoznam všetkých stavov ako klikateľné riadky
- Aktívny stav zvýraznený (CSS `--primary`)
- Počet akcií v onEnter + timeline ako badge
- Transition šípky ako malé tagy (`→ NEXT_STATE`)
- Stav `initialState` má zelenú ikonku `▶`
- Drag-and-drop reorder stavov (mení poradie iba v editore, nie v JSON — stavy sú dictionary)
- `[+ Nový stav]` tlačidlo dole

### Global Events sekcia
- Rozbaľovacia sekcia pod zoznamom stavov
- Zobrazuje počet globálnych eventov (emergency stop, timeout)
- Kliknutím otvorí `GlobalEventsEditor` v hlavnom paneli

### Technická poznámka
Stavový sidebar je čisto presentačný — žiadna biznis logika. Dostáva `states[]`, `selectedStateId`, `onSelectState`, `initialState` ako props.

---

## 6. Panel 2: Hlavný Editor Panel (stred)

### Sekcia: State Metadata
- Input: Názov stavu (ID) — `font-mono`, validácia (len `[A-Z0-9_]`, uppercase)
- Input: Popis (textový)
- Checkbox/radio: `isInitialState`
- Rename propagácia: zmena mena aktualizuje všetky `goto:` referencie v celej scéne

### Sekcia: onEnter / onExit
Vertikálny zoznam akcií, každá akcia ako riadok:

```
[drag handle] [action type badge] [payload editor] [delete]
```

**Drag-and-drop reorder** v rámci zoznamu pomocou `@dnd-kit/sortable`.

**Action type badge** (`mqtt` / `audio` / `video`) — kliknutím zmení typ.

**Payload editor** — závisí od typu:
- `mqtt`: `[topic input] → [message input]` — topic je dropdown zo zariadení (DevicePalette) alebo manuálny input
- `audio`: `[file dropdown z API] [volume slider 0.0-1.0]` — generuje `PLAY:filename.wav:0.8`
- `video`: `[príkaz dropdown: PLAY_VIDEO / STOP_VIDEO / PAUSE_VIDEO]` + `[file dropdown]`

**Drop zone**: Zariadenie/audio súbor z palety sa dá pretiahnuť priamo sem → vytvorí novú akciu.

### Sekcia: Visual Timeline (hlavný nový feature — viď §7)

### Sekcia: Transitions
Zoznam prechodov. Každý prechod:

```
[type dropdown] [parametre podla typu] -> [GOTO dropdown zo stavov] [delete]
```

| Type | Parametre |
|------|-----------|
| `timeout` | `delay: [number input]s` |
| `mqttMessage` | `topic: [input]` `message: [input]` |
| `audioEnd` | `target: [file dropdown]` |
| `videoEnd` | `target: [file dropdown]` |
| `always` | (žiadne parametre) |

`GOTO` dropdown zobrazuje všetky stavy + špeciálne `END`.

---

## 7. Visual Timeline Editor (FL Studio štýl)

Toto je **jadro SceneGenV2** — nahradenie textového zoznamu `{ at: ..., action: ... }` vizuálnym horizontálnym plátnom.

### Konceptuálny model

```
Cas (s):  0---------1---------2---------3---------4---------5---------6---------7---------8---------9--------10
          |                                                                                                    |
MQTT      |  *[light/fire ON]              *[smoke ON]                                           *[smoke OFF] |
          |                                                                                                    |
AUDIO     |  *[atmosfera.wav 0.5vol]                                                                          |
          |                                                                                                    |
VIDEO     |  *[STOP_VIDEO]                                                                                    |
          +----------------------------------------------------------------------------------------------------+
```

Každý `*` bod je jeden `TimelineItem` zo schémy (`{ at: 1.4, action: 'mqtt', ... }`).

### Stopy (Tracks)

Tri fixné stopy:
1. **MQTT track** — všetky `action: 'mqtt'` timeline položky
2. **Audio track** — všetky `action: 'audio'` timeline položky
3. **Video track** — všetky `action: 'video'` timeline položky

Každá stopa má farebnú akcentáciu zodpovedajúcu design systému:
- MQTT: `var(--primary)` (indigo)
- Audio: `var(--success)` (zelená)
- Video: `var(--color-video)` (ružová — existuje v theme.css)

### Clip (bod na timeline)

```
+-----------------------+
| bolt light/fire ON    |
| @ 1.4s                |
+-----------------------+
```

- Fixná šírka (~180px) — clip NIE JE proporcionálny trvaniu (lebo timeline položky sú body, nie intervaly)
- Obsahuje: ikonu action type + skrátený popis + čas
- Hover: tooltip s plným popisom
- Kliknutie: otvorí inline editor payload v clip paneli alebo v pravom property paneli
- **Drag horizontálne**: presúva clip po osi X → mení hodnotu `at` v reálnom čase
- **Snap to grid**: voliteľný, default 0.1s snap (viditeľné gridlines na ruleroy)
- `[x]` tlačidlo pre zmazanie

### Time Ruler

```
0s       1s       2s       3s       4s       5s
|--------+--------+--------+--------+--------+
```

- Hlavné tickmarky každú 1s, menšie každých 0.1s (pri dostatočnom zoome)
- Kliknutie na ruler: presúva "playhead" pozíciu (len vizuálny marker, nehrá reálne)
- Dĺžka osi sa automaticky nastavuje na `max(at) + buffer` alebo na `transition.delay` stavu

### Zoom a Scroll

- Horizontálny zoom: `+` / `-` tlačidlá alebo `Ctrl + scroll` (mení `pixelsPerSecond`)
- Horizontálny scroll keď obsah presahuje viewport
- Minimálny zoom: 40px/s, maximálny: 400px/s, default: 80px/s
- Snap toggle: checkbox v toolbare timeline

### Interakcie (Drag na timeline)

**Presúvanie existujúceho clipu**:
```
onPointerDown -> record startX, startAt
onPointerMove -> deltaX / pixelsPerSecond -> newAt (snap ak je aktivny)
onPointerUp   -> commit newAt do state
```
Implementácia cez natívne pointer events — je to najspoľahlivejší spôsob pre pixel-to-time transformácie. Žiadna externá knižnica toto nevyrieši lepšie.

**Pridanie novej akcie na timeline**:
1. Ťahanie z `ActionPalette` na track → drop → vytvorí nový TimelineItem na pozícii `dropX / pixelsPerSecond`
2. Dvojklik na prázdnu plochu tracku → vytvorí novú akciu na pozícii kliknutia

**Trvanie akcie (voliteľné vizuálne)**:
Pre audio clipy kde je zrejmé trvanie (WAV súbor má metadata) môže byť clip vizuálne natiahnutý — ale `at:` zostáva bod, nie interval. Trvanie je len vizuálna nápoveda.

### Technická implementácia

**NE-použiť** pre timeline drag žiadnu knižnicu (react-dnd, @dnd-kit) — pixel-to-time matematika si vyžaduje custom pointer handling. Knižnice sú určené pre reorder listov, nie pre kontinuálnu os.

**Použiť** `@dnd-kit` iba pre:
- Reorder akcií v `ActionListEditor` (onEnter/onExit)
- Drag z `ActionPalette` na track (drop detection cez `useDraggable` + `useDroppable`)

### Pseudokód useTimelineDrag hook

```js
// hooks/useTimeline.js
function useTimelineDrag({ item, pixelsPerSecond, snap, snapInterval, onChange }) {
  const startRef = useRef(null);

  function onPointerDown(e) {
    e.currentTarget.setPointerCapture(e.pointerId);
    startRef.current = { clientX: e.clientX, originalAt: item.at };
  }

  function onPointerMove(e) {
    if (!startRef.current) return;
    const deltaX = e.clientX - startRef.current.clientX;
    const deltaSeconds = deltaX / pixelsPerSecond;
    let newAt = Math.max(0, startRef.current.originalAt + deltaSeconds);
    if (snap) newAt = Math.round(newAt / snapInterval) * snapInterval;
    onChange({ ...item, at: +newAt.toFixed(2) });
  }

  function onPointerUp() {
    startRef.current = null;
  }

  return { onPointerDown, onPointerMove, onPointerUp };
}
```

---

## 8. Panel 3: Paleta (pravý panel)

### DevicePalette — napojenie na `devices.json`

Aktuálny SceneGen má zariadenia hardcoded v `constants.js`. SceneGenV2 ich načíta zo servera:

```js
// Existujuci hook, len ho pouzijeme
const { devices, motors, relays } = useDevices();
```

Paleta zobrazuje karty zariadení zoskupené podľa typu:
- `motors` → Motor 1 (Kolesá), Motor 2 (Hodiny) — s rýchlym builderom správy `ON:75:R:1000`
- `relays` + `lights` → jednoduché ON/OFF/BLINK karty

Každá karta má:
- Label zo `devices.json` (napr. "Svetlo 1", "Dymostroj")
- MQTT topic (napr. `room1/light/1`)
- Predvolené správy ako tlačidlá (ON / OFF)
- **Drag handle** — pretiahnuť na:
  - `onEnter`/`onExit` zoznam → pridá akciu
  - `VisualTimeline` track → pridá TimelineItem na pozíciu dropu

Zariadenia z `devices.json` majú topic ako `{room}/{device_id}`. Hook `useDevicePalette.js` transformuje raw devices.json štruktúru na palette items (normalizácia motors, relays, lights do jednotného formátu).

### AudioPalette — napojenie na `/api/media/audio`

```js
// Existujuci hook
const { audios } = useMedia();
```

Zobrazuje zoznam dostupných audio súborov s:
- Menom súboru
- Tlačidlo preview (volá `api.playMedia('audio', filename)`)
- Drag handle → generuje `{ action: 'audio', message: 'PLAY:filename.wav:1.0' }`
- Volume slider (0.0–1.0) pred dragom — nastaví výsledný volume v message

### VideoPalette

Podobne ako AudioPalette, ale pre video súbory. Drag generuje `{ action: 'video', message: 'PLAY_VIDEO:filename.mp4' }`.

### Custom MQTT

Text input pre manuálne zadanie topic + message — pre zariadenia, ktoré nie sú v `devices.json` (ESP32 custom, debug topics atď.).

---

## 9. Bottom Tabs

Tri záložky prepínajú hlavný pohľad:

| Tab | Obsah |
|-----|-------|
| **Editor** | State metadata + onEnter + VisualTimeline + onExit + Transitions |
| **Flow Graf** | Existujúca `SceneVisualizer` (ReactFlow, read-only) — import z `components/Scenes/SceneVisualizer.jsx` |
| **JSON Preview** | Monaco editor (read-only alebo editable) — existujúci `@monaco-editor/react` |

`Flow Graf` a `JSON Preview` sú read-only pohľady na aktuálnu scénu — vygenerované live z editora.

---

## 10. Správa Stavu (`useSceneEditor.js`)

Centrálny hook je evolúcia `useSceneManager.js` zo SceneGen:

```js
const {
  // Metadata
  sceneId, description, version, initialState, globalPrefix,

  // States
  states,           // State[]
  selectedStateId,  // string | null
  globalEvents,     // Transition[]

  // Actions
  selectState,        // (id) => void
  addState,           // () => string (returns new id)
  updateState,        // (id, partial) => void
  deleteState,        // (id) => void
  renameState,        // (id, newName) => void -- propaguje vsetky goto refs
  reorderStates,      // (oldIndex, newIndex) => void

  updateMetadata,     // (partial) => void
  setGlobalEvents,    // (events) => void

  // Timeline specific
  addTimelineItem,    // (stateId, item) => void
  updateTimelineItem, // (stateId, itemId, partial) => void
  deleteTimelineItem, // (stateId, itemId) => void
  moveTimelineItem,   // (stateId, itemId, newAt) => void

  // Persistence
  saveToBackend,      // () => Promise<void> -- calls api.saveScene()
  exportJSON,         // () => string
  importJSON,         // (jsonString) => void
  isDirty,            // boolean -- unsaved changes

} = useSceneEditor({ sceneName, initialData });
```

**LocalStorage** — rovnaká stratégia ako v aktuálnom SceneGen — auto-save každú zmenu pre recovery.

**Backend save** — `api.saveScene(sceneName, jsonData)` — existuje a funguje.

---

## 11. Nové Knižnice (len 1 nová závislosť)

```json
"@dnd-kit/core": "^6.x",
"@dnd-kit/sortable": "^8.x"
```

**Prečo @dnd-kit**:
- Moderná náhrada za `react-beautiful-dnd` (deprecated)
- Lightweight, accessible, tree-shakeable
- Perfektný pre **sortable listy** (reorder onEnter/onExit akcií) a **drag z palety** na track cez `useDraggable` + `useDroppable`
- Dashboard zatiaľ nemá žiadnu drag-and-drop knižnicu

**Čo @dnd-kit NERIEŠI** (a prečo):
- Timeline clip dragging — to je custom pointer events (pixely → sekundy matematika); žiadna DnD knižnica to nevyrieši, lebo nepozná pojem "časová os"

**Čo sa NEpridáva**:
- `react-resizable` — klipse nepotrebujú resize (sú body v čase, nie intervaly)
- `wavesurfer.js` — overkill pre audio paletu, stačí `HTMLAudioElement` preview
- `react-virtualized` — timeline má realisticky < 50 clipov, virtualizácia zbytočná
- `react-draggable` — je v starom SceneGen, ale pre dashboard je @dnd-kit lepšia voľba

---

## 12. API Integrácia

Všetky potrebné API volania **už existujú** v `museum-dashboard/src/services/api.js`:

| Potreba | Existujúce API |
|---------|----------------|
| Načítanie scény | `api.getSceneContent(sceneName)` |
| Uloženie scény | `api.saveScene(sceneName, data)` |
| Zoznam scén | `api.getScenes()` |
| Zariadenia | `api.getDevices()` → `{ motors, relays, lights }` |
| Audio súbory | `api.getMedia('audio')` → pole file objektov s `.name` |
| Video súbory | `api.getMedia('video')` |
| Preview audio | `api.playMedia('audio', filename)` |

**NOVÉ API volanie** — voliteľné pre SceneGenV2:

```python
# raspberry_pi/Web/routes/media.py -- novy endpoint
@bp.route('/api/media/audio/<filename>/duration', methods=['GET'])
def get_audio_duration(filename):
    # Vrati dlzku WAV/MP3 v sekundach pre vizualnu reprezentaciu v timeline
    # Pouzitie: standardna kniznica 'wave' alebo mutagen
```

Toto je nice-to-have — umožní vizuálne zobraziť trvanie audio clipu na timeline ako nápovedu.

---

## 13. Štýlovanie (dodržanie design systému)

Všetky štýly musia:
- Používať CSS premenné z `theme.css` (NIKDY hardcoded hex)
- Reusable komponent štýly → `components.css`
- View-specific štýly → `styles/views/scene-editor-v2.css`
- Existujúce UI komponenty: `Button`, `Card`, `Modal`, `StatusBadge`, `PageHeader`

**Nové CSS premenné potrebné v `theme.css`** (ak ešte neexistujú):

```css
/* Timeline farebne stopy */
--timeline-track-mqtt:  var(--primary);
--timeline-track-audio: var(--success);
--timeline-track-video: var(--color-video);   /* uz existuje */
--timeline-ruler-bg:    var(--bg-dark);
--timeline-clip-bg:     var(--bg-card);
--timeline-clip-border: var(--border-color);
--timeline-grid-line:   var(--border-color);
--timeline-playhead:    var(--warning);
```

**Výšky stôp**: fixná výška jednej stopy = `52px`, ruler = `32px`.

Dashboard má light + dark theme cez `data-theme='dark'` — timeline musí vyzerať dobre v oboch.

---

## 14. Reuse existujúceho kódu zo SceneGen

Nasledujúce časti SceneGen sa PRENÁŠAJÚ (reimplementujú v dashboard štýle, nie Tailwind):

| SceneGen komponent | Dashboard ekvivalent |
|--------------------|----------------------|
| `useSceneManager.js` | `useSceneEditor.js` (rozšírený) |
| `jsonExport.js` | Rovnaká logika `generateStateMachineJSON`, `importJSON` |
| `StateEditor.jsx` (metadata + sekcie) | `StatePanel.jsx` + `StateMetaForm.jsx` |
| `ActionListEditor.jsx` | `ActionListEditor.jsx` (+ @dnd-kit sortable) |
| `TransitionEditor.jsx` | `TransitionEditor.jsx` |
| `GlobalEventsEditor.jsx` | `GlobalEventsEditor.jsx` |
| `generators.js` (createEmptyState, createEmptyAction, generateId) | Prenesie sa 1:1 |
| `GraphicPreview.jsx` | **Existujuci** `SceneVisualizer.jsx` v dashboarde |

Čo je v SceneGen a NEprenesie sa:
- Tailwind CSS (dashboard nemá Tailwind)
- `App.jsx` layout (nahradí ho nový View)
- `constants.js / MQTT_DEVICES` (nahradí real-time `useDevices`)
- `Sidebar.jsx` zo SceneGen (iný layout ako dashboard Sidebar)

---

## 15. Implementačný plán (fázy)

### Fáza 1 — Základ (MVP editor bez vizuálnej timeline)
Cieľ: Funkčný editor stavov v dashboarde, parita s aktuálnym SceneGen.

1. Vytvoriť `useSceneEditor.js` hook (portovanie `useSceneManager`)
2. Vytvoriť `SceneEditorView.jsx` s 3-panel layoutom (zatiaľ bez vizuálnej timeline)
3. Portovať `ActionListEditor`, `TransitionEditor`, `GlobalEventsEditor`
4. Pridať `@dnd-kit/sortable` pre reorder onEnter/onExit
5. Napojenie na `api.getSceneContent` + `api.saveScene`
6. Nahradiť `SceneEditorModal` týmto editorom v `ScenesView`

### Fáza 2 — Device & Audio palety
Cieľ: Palety namiesto hardcoded constants.

1. `useDevicePalette.js` — transformácia `useDevices()` na palette items
2. `DevicePalette.jsx` + `AudioPalette.jsx` komponent
3. `@dnd-kit` drag z palety → drop na `ActionListEditor`
4. Preview tlačidlo pre audio súbory (volá existujúci `api.playMedia`)

### Fáza 3 — Visual Timeline
Cieľ: FL Studio-štýl timeline namiesto textového zoznamu.

1. `TimeRuler.jsx` — SVG ruler so tickmarkami
2. `TimelineTrack.jsx` — horizontálna stopa s clipmi (CSS position absolute pre X)
3. `TimelineClip.jsx` + `useTimeline.js` — pointer events drag
4. `VisualTimeline.jsx` — orchestrátor všetkých stôp + scroll container
5. Zoom + snap controls v `TimelineToolbar.jsx`
6. Drop zone — `useDroppable` z @dnd-kit → nový clip na pozícii dropu
7. `moveTimelineItem` v `useSceneEditor`

### Fáza 4 — Polish a integrácia
1. Validácia pri ukladaní (frontend echo logiky `schema_validator.py`)
2. `isDirty` indikátor (badge v headeri)
3. Keyboard shortcuts (Delete = zmazať vybraný clip, Ctrl+Z = undo základný)
4. Voliteľný backend endpoint pre audio duration
5. Migrácia standalone SceneGen — ponechať ako offline dev nástroj

---

## 16. Hraničné prípady a riziká

### 1. Timeline položky s `actions[]` (multi-akcia v jednom bode)
Schéma podporuje `{ at: 1.0, actions: [Action1, Action2] }`. V aktuálnom SceneGen sa toto nepoužíva. V SceneGenV2 to zjednodušiť: každý clip = jedna akcia. Ak import nájde `actions[]`, rozexploduje ich na viaceré clipse na rovnakom `at`.

### 2. Kolízie clipov na rovnakom `at`
Dva clipse na rovnakom čase v tej istej stope sa vizuálne prekryjú. Riešenie: neblokujeme to (schéma to dovoľuje), ale vizuálne ich posunieme `y`-ovo o `+8px` ako stack indikátor.

### 3. Rename stavu
Zmena mena stavu musí aktualizovať všetky `goto:` referencie v celej scéne (vrátane `globalEvents`). Toto je kritická logika — `useSceneEditor.renameState` musí prejsť celou scénou. Aktuálny SceneGen to má v `useSceneManager.updateState` — rovnakú logiku preniesť 1:1.

### 4. Veľké scény (20+ stavov)
Sidebar s 20+ stavmi — možno pridať filter/search input do `StateList`. Vizuálna timeline zostáva manageable keďže každý stav sa pozerá izolovaný (nie všetky stavy naraz na jednej timeline).

### 5. Autosave vs. manuálne uloženie
Dashboard má backend (na rozdiel od standalone SceneGen). Preto: autosave do `localStorage` (recovery), ale **manuálne save** na Pi cez tlačidlo "Uložiť na Pi" s `react-hot-toast` potvrdením. Indikátor `isDirty` ukazuje nezapísané zmeny.

---

## 17. Rozhodnutia, ktoré treba urobiť pred implementáciou

1. **Kde žije SceneEditorV2 v UI?**
   - A) Nový route `/scene-editor/:name` (full-page, odporúčané)
   - B) Upgrade existujúceho `SceneEditorModal` na large overlay

2. **Standalone SceneGen — čo s ním?**
   - A) Zachovať ako offline dev nástroj (bez backendu)
   - B) Deprecovať po dokončení V2
   - C) Refaktorovať aby používal rovnaký `useSceneEditor` hook (zdieľaná logika)

3. **Undo/Redo?**
   - Implementovať od začiatku (history stack v `useSceneEditor`) alebo skip pre V1?

4. **Audio duration API endpoint?**
   - Pridať do Pi backendu (jednoduchý `wave` modul, trivial) alebo skip?

---

## Záver a realizovateľnosť

**Áno, je to realizovateľné.** Všetky kľúčové prerekvizity sú splnené:

- Schéma je čistá a dobre zdokumentovaná — editor môže generovať valídny JSON
- Backend API pre devices, media, scenes existuje a funguje
- `reactflow`, `monaco-editor`, `react-hot-toast` sú v dashboarde
- Existujúci `SceneVisualizer` je read-only Flow Graf — môžeme ho priamo zaradiť do V2 tabs
- Existujúci `useDevices` a `useMedia` hooks napájajú paletu bez nového API

**Najnáročnejšia časť** je Visual Timeline (Fáza 3) — konkrétne pointer events drag s pixel-to-time transformáciou a drop detection z palety. Toto je custom implementácia (~300–400 riadkov v `useTimeline.js` + `VisualTimeline.jsx`), ale žiadna knižnica toto za nás nevyrieši inak. FL Studio-štýl timeline pre event data (nie audio waveforms) je inherentne custom logika.

**Dôvod prečo integrovať do dashboardu a nie standalone SceneGen rozšíriť:**  
Standalone SceneGen nemá a nemôže mať prístup k `devices.json` ani audio knižnici bez toho, aby sme doň pridali autentizáciu + API vrstvu — čo by duplikovalo celý dashboard backend. Integrácia do dashboardu je správna architektúra.
