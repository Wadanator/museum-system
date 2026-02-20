# Videos pre `room1`

Sem ukladaj video súbory používané scénami pre room1.

---

## Podporované formáty (`video_handler.py`)

- `.mp4`
- `.avi`
- `.mkv`
- `.mov`
- `.webm`

---

## Použitie v scene JSON

### Priamy názov súboru
```json
{ "action": "video", "message": "intro.mp4" }
```

### Explicitný príkaz
```json
{ "action": "video", "message": "PLAY_VIDEO:intro.mp4" }
```

Ďalšie commandy:
- `STOP_VIDEO`
- `PAUSE`
- `RESUME`
- `SEEK:<seconds>`

---

## Dôležité

- názov súboru v scéne musí presne sedieť,
- cesta je relatívna k video directory nastavenej v `config.ini`,
- po `STOP_VIDEO` sa načíta idle obrázok (`iddle_image`).
