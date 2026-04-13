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

`handle_command()` najprv skúsi rozpoznať explicitný príkaz. Ak príkaz nezačne `PLAY_VIDEO:`, `STOP_VIDEO`, `PAUSE`, `RESUME` alebo `SEEK:`, handler ho berie ako názov súboru a skúsi ho prehrať priamo.

`PLAY_VIDEO:` vždy smeruje na `play_video()`. `STOP_VIDEO` vráti prehrávanie na idle obrázok, `PAUSE` a `RESUME` ovládajú mpv pauzu a `SEEK:<seconds>` používa absolútne seekovanie v sekundách.

---

## 2) Ako je implementované prehrávanie

`VideoHandler`:
- spúšťa/udržiava `mpv` proces,
- používa UNIX IPC socket (`ipc_socket` z configu),
- má health-check interval,
- pri neodpovedajúcom mpv vie vykonať reštart s cooldownom/limitom.

V runtime ho vytvára `ServiceContainer` z config hodnôt:
- `video_dir`
- `ipc_socket`
- `iddle_image`
- `video_health_check_interval`
- `video_max_restart_attempts`
- `video_restart_cooldown`

`VideoHandler` vytvára idle obrázok automaticky, ak neexistuje. Pri štarte spúšťa `mpv` s fullscreen režimom, `--image-display-duration=inf`, `--loop-file=inf`, `--idle=yes` a IPC socketom.

`STOP_VIDEO` nahrá idle obrázok (`iddle_image` v confige). Pri prehrávaní videa handler do playlistu pridá idle obrázok ako ďalšiu položku, aby mpv po dohraní prepol obraz bez medzery.

`play_video()` odmietne súbor, ak neexistuje v `video_dir` alebo nemá podporovanú príponu.

`_detect_hwdec()` používa Debian verziu: Bookworm / Debian 12+ → `v4l2`, Bullseye / Debian 11 alebo neznáme → `rpi4-mmal`.

Health-check kontroluje, či proces beží, či existuje IPC socket a či socket odpovedá na IPC dotaz. Ak kontrola zlyhá, handler skúsi reštart.

`check_if_ended()` zisťuje koniec videa podľa zmeny stavu prehrávania. Keď prechod z "hrá" na "nehrá" nastane, uloží názov skončeného súboru, prepne na idle obraz a až potom zavolá end callback.

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

`SceneParser.process_scene()` pri každom ticku volá `video_handler.check_if_ended()`.
Pri dohraní:
1. `VideoHandler` zavolá end callback s názvom skončeného súboru,
2. `SceneParser` presunie túto udalosť do `TransitionManager.register_video_end()`,
3. prechod typu `videoEnd` sa môže splniť, ak sa `target` zhoduje s názvom skončeného súboru.

`videoEnd` porovnáva presný názov súboru, nie len príponu alebo časť mena.

`TransitionManager` spracuje udalosť len raz; po úspešnom prechode ju z fronty odstráni.

---

## 5) Typické problémy

- Video súbor nie je v `[Video] directory`.
- Zlá prípona/nepodporovaný formát.
- `target` vo `videoEnd` nesedí s názvom prehrávaného súboru po presnom porovnaní.
- mpv IPC socket je neplatný alebo mpv sa nespustil.
- mpv sa neobnovil po health-check chybe alebo sa zasekol na IPC komunikácii.

Pri debugovaní sleduj video logger + backend logy.
