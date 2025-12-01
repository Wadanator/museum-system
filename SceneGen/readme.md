# State Machine Scene Editor

Vizuálny editor pre tvorbu JSON scén v State Machine formáte pre múzejný systém. Aplikácia umožňuje intuitívne vytváranie stavov, akcií a prechodov s možnosťou grafického náhľadu.

## 🚀 Inštalácia a spustenie

Keďže projekt je už vytvorený, stačí nainštalovať závislosti a spustiť ho.
```bash
# 1. Prejdi do priečinka editora
cd SceneGen

# 2. Nainštaluj závislosti
yarn install

# 3. Spusti vývojový server
yarn dev
```

## 📁 Štruktúra projektu

Projekt bol reorganizovaný do modulárnej štruktúry pre lepšiu prehľadnosť a údržbu:
```
SceneGen/
├── src/
│   ├── components/
│   │   ├── features/
│   │   │   ├── editor/    # Logika editácie stavov (StateEditor, ActionEditor...)
│   │   │   ├── graph/     # Grafický náhľad (GraphicPreview, SceneNode)
│   │   │   ├── mqtt/      # Komponenty pre MQTT zariadenia (Motor, Audio, Video...)
│   │   │   └── settings/  # Globálne nastavenia a udalosti
│   │   ├── layout/        # Rozloženie stránky (Header, Sidebar, Toolbar)
│   │   └── ui/            # Všeobecné UI prvky (ak existujú)
│   ├── hooks/             # Vlastné React hooks (useSceneManager)
│   ├── utils/
│   │   ├── constants.js   # Konštanty a definície zariadení
│   │   ├── generators.js  # Generátory prázdnych objektov
│   │   └── jsonExport.js  # Export/Import JSON logika
│   ├── App.jsx            # Hlavná aplikácia a routing
│   ├── main.jsx           # Entry point
│   └── index.css          # Tailwind štýly
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## ✨ Funkcie

### 📊 Editor Stavov
- **Pridávanie a mazanie stavov** - Komplexná správa životného cyklu scény.
- **Detailná editácia** - Nastavenie onEnter (vstup), Timeline (časová os) a onExit (výstup) akcií.
- **Sidebar navigácia** - Rýchly presun medzi stavmi pomocou bočného panelu.

### ⚡ Pokročilé Akcie (MQTT)
**Preddefinované zariadenia** - Jednoduché ovládanie pre:
- Motory (Rýchlosť, Smer)
- Svetlá, Dym, Para (ON/OFF)
- Audio prehrávač (Play, Volume)
- Video prehrávač (Play, Loop)

**Custom MQTT** - Možnosť zadať ľubovoľný topic a message.

### 🕸️ Grafický Náhľad (Node Graph)
- **Vizualizácia** - Zobrazenie celej scény ako orientovaného grafu.
- **Interaktivita** - Kliknutím na uzol (node) sa editor presunie na daný stav.
- **Vizuálna tvorba** - Pridávanie stavov priamo z grafu.

### 🔄 Prechody (Transitions)
- **Timeout** - Automatický prechod po uplynutí času.
- **MQTT Message** - Reakcia na správu zo siete.
- **Button Press** - Reakcia na fyzické tlačidlo v múzeu.
- **Audio/Video End** - Prechod po skončení média.

### 💾 Import/Export
- **Generovanie JSON** - Validný výstup pre Raspberry Pi kontrolér.
- **Načítanie scény** - Možnosť pokračovať v práci na existujúcom súbore.

## 📝 Príklad vygenerovaného JSON
```json
{
  "sceneId": "room1_intro",
  "description": "Úvodná show",
  "version": "2.0",
  "initialState": "start",
  "globalPrefix": "room1",
  "states": {
    "start": {
      "onEnter": [
        {"topic": "room1/light", "message": "OFF"},
        {"topic": "room1/audio", "message": "PLAY:welcome.mp3"}
      ],
      "transitions": [
        {"type": "audioEnd", "goto": "main_show"}
      ]
    },
    "main_show": {
      "timeline": [
        {"at": 2.0, "topic": "room1/motor1", "message": "ON:50:L"}
      ],
      "transitions": [
        {"type": "timeout", "delay": 10.0, "goto": "end"}
      ]
    }
  }
}
```

## 🛠️ Technológie

- **React 18** - UI framework
- **Vite** - Rýchly build tool
- **Tailwind CSS** - Moderné štýlovanie
- **React Flow** - Knižnica pre grafové zobrazenie uzlov
- **Lucide React** - Ikony

## 🔧 Rozšírenie o nové zariadenie

Ak chceš pridať nové zariadenie do ponuky (napr. nový typ senzora):

1. Otvor `src/utils/constants.js`.
2. Nájdi objekt `MQTT_DEVICES`.
3. Pridaj novú definíciu:
```javascript
novy_senzor: {
  label: 'Nový Senzor',
  type: 'simple', // alebo 'motor', 'audio' atď.
  commands: ['KALIBROVAT', 'RESET']
}
```

4. Reštartuj aplikáciu, zariadenie sa objaví v Action editore.