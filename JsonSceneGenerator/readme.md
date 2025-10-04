# State Machine Scene Editor

Vizuálny editor pre tvorbu JSON scén v State Machine formáte pre múzejný systém.

## 🚀 Inštalácia a spustenie

```bash
# 1. Vytvor projekt
yarn create vite state-machine-editor --template react

# 2. Prejdi do priečinka
cd state-machine-editor

# 3. Nainštaluj závislosti
yarn

# 4. Nainštaluj dodatočné balíčky
yarn add lucide-react
yarn add -D tailwindcss postcss autoprefixer

# 5. Inicializuj Tailwind
npx tailwindcss init -p

# 6. Skopíruj všetky súbory z artefaktov do projektu

# 7. Spusti vývojový server
yarn dev
```

## 📁 Štruktúra projektu

```
state-machine-editor/
├── src/
│   ├── components/
│   │   ├── ActionEditor.jsx       # Editor akcií (MQTT, audio, video)
│   │   ├── TimelineEditor.jsx     # Timeline s časovanými akciami
│   │   ├── TransitionEditor.jsx   # Prechody medzi stavmi
│   │   ├── StateEditor.jsx        # Editor jednotlivého stavu
│   │   └── Header.jsx             # Hlavička s metadátami scény
│   ├── utils/
│   │   ├── constants.js           # Konštanty a typy
│   │   ├── generators.js          # Generátory prázdnych objektov
│   │   └── jsonExport.js          # Export/Import JSON logika
│   ├── App.jsx                    # Hlavná aplikácia
│   ├── main.jsx                   # Entry point
│   └── index.css                  # Štýly
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## ✨ Funkcie

### 📊 State Management
- **Pridávanie stavov** - vytvorenie nových stavov scény
- **Editácia stavov** - názov, popis, akcie
- **Mazanie stavov** - odstránenie nepotrebných stavov

### ⚡ Actions (Akcie)
- **MQTT** - topic + message (napr. `room1/light` → `ON`)
- **Audio** - prehranie audio súboru
- **Video** - prehranie video súboru

### 📅 Timeline
- **Časované akcie** - akcie s presným časom v rámci stavu
- Napr.: "po 3 sekundách zapni motor"

### 🔄 Transitions (Prechody)
- **Timeout** - prechod po určitom čase
- **MQTT Message** - čakanie na správu z MQTT
- **Button Press** - čakanie na stlačenie tlačidla

### 💾 Import/Export
- **Export JSON** - stiahnutie v správnom formáte
- **Import JSON** - načítanie existujúcej konfigurácie
- **Preview** - náhľad vygenerovaného JSON

## 📝 Príklad vygenerovaného JSON

```json
{
  "sceneId": "test_intro",
  "description": "Testovacia scéna",
  "version": "2.0",
  "initialState": "intro",
  "states": {
    "intro": {
      "description": "Úvodná scéna",
      "onEnter": [
        {"action": "mqtt", "topic": "room1/light", "message": "ON"},
        {"action": "mqtt", "topic": "room1/motor1", "message": "ON:50:L"}
      ],
      "timeline": [
        {"at": 3.0, "action": "mqtt", "topic": "room1/motor2", "message": "ON:30:R"}
      ],
      "transitions": [
        {"type": "timeout", "delay": 5.0, "goto": "middle"}
      ]
    },
    "middle": {
      "description": "Stredná časť",
      "onEnter": [
        {"action": "mqtt", "topic": "room1/motor1", "message": "OFF"}
      ],
      "transitions": [
        {"type": "timeout", "delay": 4.0, "goto": "END"}
      ]
    }
  }
}
```

## 🎯 Používanie

1. **Vytvor stavy** - pridaj stavy scény (intro, middle, finale)
2. **Definuj akcie** - pridaj onEnter, timeline, onExit akcie
3. **Nastav prechody** - definuj kedy prejsť do ďalšieho stavu
4. **Exportuj JSON** - stiahni hotovú konfiguráciu
5. **Použij v systéme** - nahraj JSON do `raspberry_pi/scenes/`

## 🛠️ Technológie

- **React** - UI framework
- **Vite** - build tool
- **Tailwind CSS** - styling
- **Lucide React** - ikony

## 📖 Modularita

Projekt je rozdelený do modulárnych komponentov pre lepšiu údržbu:
- Každý komponent má svoju zodpovednosť
- Utils funkcie sú oddelené
- Konštanty sú centralizované
- Jednoduchá rozšíriteľnosť

## 🔧 Rozšírenie

Pridanie nového typu akcie:
1. Pridaj typ do `utils/constants.js`
2. Uprav `createEmptyAction` v `utils/generators.js`
3. Pridaj UI do `components/ActionEditor.jsx`

## 📄 Licencia

MIT