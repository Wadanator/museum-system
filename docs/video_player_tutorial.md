# Video v scénach – praktický návod

Video vykonáva modul:
- `raspberry_pi/utils/video_handler.py`

Scéna používa akciu:
```json
{ "action": "video", "message": "..." }
```

---

## 1) Podporované commandy (`handle_command`)

- `PLAY_VIDEO:<filename>`
- `STOP_VIDEO`
- `PAUSE`
- `RESUME`
- `SEEK:<seconds>`
- alebo priamo názov súboru (`scene1.mp4`)

Podporované prípony:
- `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`

---

## 2) Ako je implementované prehrávanie

`VideoHandler`:
- spúšťa/udržiava `mpv` proces,
- používa UNIX IPC socket (`ipc_socket` z configu),
- má health-check interval,
- pri neodpovedajúcom mpv vie vykonať reštart s cooldownom/limitom.

`STOP_VIDEO` nahrá idle obrázok (`iddle_image` v confige).

---

## 3) Príklady scén

## 3.1 Prehraj video a prejdi po dohraní
```json
{
  "sceneId": "video_end_demo",
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

## 3.2 Timeline video commandy
```json
{
  "sceneId": "video_timeline_demo",
  "initialState": "s1",
  "states": {
    "s1": {
      "timeline": [
        { "at": 0.0, "action": "video", "message": "PLAY_VIDEO:loop.mp4" },
        { "at": 2.5, "action": "video", "message": "SEEK:10" },
        { "at": 6.0, "action": "video", "message": "PAUSE" },
        { "at": 7.0, "action": "video", "message": "RESUME" }
      ],
      "transitions": [
        { "type": "timeout", "delay": 12, "goto": "END" }
      ]
    }
  }
}
```

---

## 4) Prepojenie s transition managerom

`SceneParser.check_if_ended()` sleduje prechod z „hrá“ na „dohrané“.
Pri dohraní:
1. zavolá callback,
2. transition manager zaregistruje `videoEnd` event,
3. `videoEnd` transition môže preskočiť do ďalšieho stavu.

---

## 5) Typické problémy

- Video súbor nie je v `[Video] directory`.
- Zlá prípona/nepodporovaný formát.
- `target` vo `videoEnd` nesedí s názvom prehrávaného súboru.
- mpv IPC socket je neplatný alebo mpv sa nespustil.

Pri debugovaní sleduj video logger + backend logy.
