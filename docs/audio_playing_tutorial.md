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
- `STOP`
- `STOP:<filename>`
- `PAUSE`
- `RESUME`
- `VOLUME:<0-1>`
- alebo priamo názov súboru, napr. `intro.mp3`

---

## 2) Ako handler prehráva zvuk

Audio handler používa dva režimy:

1. **SFX v RAM cache**
   - hlavne súbory s prefixom `sfx_`
   - môžu hrať paralelne na viacerých kanáloch

2. **Music stream z disku**
   - jeden aktívny `pygame.mixer.music` stream
   - pri štarte nového streamu sa predchádzajúci stopne

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
   - `target` musí sedieť s názvom, ktorý handler reálne prehráva.

3. **Zlá hlasitosť**
   - `VOLUME` a `PLAY:...:<volume>` používajú rozsah `0.0–1.0`.

4. **Zabudnuté pole `action`**
   - schema vyžaduje explicitné `"action": "audio"`.

---

## 6) Overenie po zmene

- spusti backend lokálne
- pusť test scénu
- sleduj logy `audio` loggera
- over, že `audioEnd` prechod nastane správne
