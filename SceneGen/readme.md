# SceneGen

Vizuálny editor pre JSON scény kompatibilné s `raspberry_pi/utils/schema_validator.py`.

## Spustenie

```bash
cd SceneGen
yarn install
yarn dev
```

## Čo editor rieši

- tvorba `states` + `initialState`
- `onEnter`, `timeline`, `onExit`
- transitions (`timeout`, `mqttMessage`, `audioEnd`, `videoEnd`, `always`)
- export/import JSON scény

## Dôležité

Výsledný JSON musí mať akcie s poľom `action` (`mqtt`, `audio`, `video`), inak backend validácia scénu odmietne.
