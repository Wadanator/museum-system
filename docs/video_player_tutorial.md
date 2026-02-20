# Video commandy v scénach

Video sa vykonáva cez `action: "video"` a spracúva `VideoHandler.handle_command()`.

## Podporované príkazy

- `PLAY_VIDEO:<file>`
- `STOP_VIDEO`
- `PAUSE`
- `RESUME`
- `SEEK:<sekundy>`
- Priamy názov súboru (napr. `scene1.mp4`) = prehratie videa.

Podporované formáty sú v kóde: `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`.

## Príklad v scene JSON

```json
{
  "sceneId": "video_demo",
  "initialState": "intro",
  "states": {
    "intro": {
      "onEnter": [
        { "action": "video", "message": "PLAY_VIDEO:scene1.mp4" }
      ],
      "transitions": [
        { "type": "videoEnd", "target": "scene1.mp4", "goto": "END" }
      ]
    }
  }
}
```

## Poznámky

- Video súbor musí byť v adresári z `[Video] directory`.
- `STOP_VIDEO` načíta idle obrázok (`iddle_image` v confige).
- Handler beží nad `mpv` IPC socketom (`ipc_socket`) a má health-check/restart logiku.
