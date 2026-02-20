# Audio commandy v scénach

Audio sa vykonáva cez `action: "audio"` a spracúva ho `AudioHandler.handle_command()`.

## Podporované príkazy (aktuálne)

- `PLAY:<file.mp3>`
- `STOP`
- `STOP:<file.mp3>`
- `PAUSE`
- `RESUME`
- `VOLUME:<0-1>`
- Priamy názov súboru (napr. `intro.mp3`) sa tiež prehrá.

> Poznámka: handler podporuje aj SFX cache/preload pre súbory so prefixom `sfx_`.

## Príklad v scene JSON

```json
{
  "sceneId": "audio_demo",
  "initialState": "start",
  "states": {
    "start": {
      "onEnter": [
        { "action": "audio", "message": "PLAY:intro.mp3" }
      ],
      "transitions": [
        { "type": "audioEnd", "target": "intro.mp3", "goto": "END" }
      ]
    }
  }
}
```

## Čo je dôležité

- Súbor musí existovať v adresári z `config.ini` (`[Audio] directory`).
- `audioEnd` transition porovnáva `target` s názvom dohraného súboru.
- Pri zmene stavu sa timeline tracking resetuje automaticky (`StateExecutor`).
