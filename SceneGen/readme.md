# SceneGen – editor scén pre museum-system

SceneGen je React/Vite nástroj na tvorbu JSON scén pre backend v `raspberry_pi/`.

---

## 1) Spustenie

```bash
cd SceneGen
yarn install
yarn dev
```

Build:
```bash
yarn build
```

---

## 2) Štruktúra projektu (aktuálna)

- `src/App.jsx` – hlavná aplikácia.
- `src/hooks/useSceneManager.js` – stav editora/scény.
- `src/utils/`
  - `constants.js`
  - `generators.js`
  - `jsonExport.js`
- `src/components/layout/`
  - `Header.jsx`
  - `Sidebar.jsx`
  - `Toolbar.jsx`

---

## 3) Cieľ exportu

Exportovaný JSON má byť kompatibilný so schema validátorom backendu:
- povinné: `sceneId`, `initialState`, `states`
- akcie musia obsahovať `action` (`mqtt`, `audio`, `video`)
- transitions musia mať `type` + `goto`

---

## 4) Odporúčaný workflow

1. Vytvor stavy + initial state.
2. Doplň `onEnter` akcie.
3. Doplň `timeline` akcie pre presné timingy.
4. Nastav transitions.
5. Export JSON.
6. Otestuj scénu v `raspberry_pi/scenes/<room_id>/`.

---

## 5) Dôležité upozornenie

Editor uľahčuje tvorbu scény, ale finálne pravidlá určujú backend moduly (`schema_validator`, `state_executor`, `transition_manager`).
Pri pridávaní nových action/transition typov treba aktualizovať backend aj editor.
