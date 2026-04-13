# Audio v scénach – praktický návod

Audio akcie vykonáva backend modul:
- `raspberry_pi/utils/audio_handler.py`

Scene engine volá audio cez akciu:
```json
{ "action": "audio", "message": "..." }
```

---

## 1) Podporované commandy (`handle_command`)

- `PLAY:<filename>`
- `PLAY:<filename>:<volume_0_1>`
- `STOP` (case-insensitive)
- `STOP:<filename>`
- `PAUSE`
- `RESUME`
- `VOLUME:<0-1>`
- alebo priamo názov súboru, napr. `intro.mp3`

`handle_command()` pri `PLAY:` rozdelí payload na názov súboru a voliteľnú hlasitosť. Ak je súbor bez prípony, handler skúsi nájsť `.mp3`, `.wav` alebo `.ogg` v audio adresári.

`STOP` zastaví všetko audio, `STOP:<filename>` zastaví iba konkrétny stream alebo SFX, `PAUSE` a `RESUME` ovplyvnia music aj všetky SFX kanály.

`VOLUME:<value>` mení iba globálnu hlasitosť music streamu. SFX hlasitosť sa nastavuje pri prehratí konkrétneho súboru cez `PLAY:`.

---

## 2) Ako handler prehráva zvuk

Audio handler používa dva režimy:

1. **SFX v RAM cache**
   - hlavne súbory s prefixom `sfx_`
   - môžu hrať paralelne na viacerých kanáloch

2. **Music stream z disku**
   - jeden aktívny `pygame.mixer.music` stream
   - pri štarte nového streamu sa predchádzajúci stopne

`play_audio_file()` najprv skontroluje RAM cache. Ak je súbor v cache, prehráva sa ako SFX na mixér kanáli. Ak v cache nie je, prehráva sa ako music stream z disku.

`preload_files_for_scene()` načítava do RAM iba súbory s prefixom `sfx_`. Pred preloadom zastaví všetko aktuálne audio a vymaže starú cache.

---

## 3) Dynamic preload pred štartom scény

Pri `SceneParser.start_scene()` sa scéna prejde a hľadajú sa audio súbory.
Súbory `sfx_...` sa preloadnú do RAM (`preload_files_for_scene`) kvôli rýchlejšiemu triggeru.

Odporúčanie:
- krátke one-shot efekty = `sfx_*`
- dlhšie hudobné stopy = stream

---

## 4) Príklady scén

## 4.1 Jednoduchý start + audioEnd transition
```json
{
  "sceneId": "audio_intro",
  "initialState": "start",
  "states": {
    "start": {
      "onEnter": [
        { "action": "audio", "message": "PLAY:intro.mp3:0.8" }
      ],
      "transitions": [
        { "type": "audioEnd", "target": "intro.mp3", "goto": "END" }
      ]
    }
  }
}
```

## 4.2 Kombinácia timeline + špecifický stop
```json
{
  "sceneId": "audio_combo",
  "initialState": "s1",
  "states": {
    "s1": {
      "timeline": [
        { "at": 0.0, "action": "audio", "message": "PLAY:music_loop.mp3:0.5" },
        { "at": 1.2, "action": "audio", "message": "PLAY:sfx_boom.wav" },
        { "at": 4.0, "action": "audio", "message": "STOP:sfx_boom.wav" }
      ],
      "transitions": [
        { "type": "timeout", "delay": 8, "goto": "END" }
      ]
    }
  }
}
```

---

## 5) Časté chyby

1. **Súbor neexistuje v audio adresári**
   - skontroluj `[Audio] directory` v `config.ini`.

2. **Nesprávny target pre `audioEnd`**
  - `target` musí sedieť s názvom súboru, ktorý handler po resolvovaní reálne eviduje interne.

3. **Zlá hlasitosť**
   - `VOLUME` a `PLAY:...:<volume>` používajú rozsah `0.0–1.0`.

4. **Zabudnuté pole `action`**
   - schema vyžaduje explicitné `"action": "audio"`.

5. **Zlý formát `audioEnd` cieľa**
   - `target` musí sedieť s názvom súboru, ktorý handler eviduje ako prehrávaný.

6. **Očakávanie globálnej hlasitosti pre SFX**
   - `set_volume()` mení len music stream, nie už prehrávané SFX kanály.

---

## 6) Overenie po zmene

- spusti backend lokálne
- pusť test scénu
- sleduj logy `audio` loggera
- over, že `audioEnd` prechod nastane správne
