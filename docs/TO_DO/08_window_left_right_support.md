# Window Left/Right Production Plan

Tento dokument nahradza povodny `cover/roleta` smer pre aktualny hardware.
Fyzicky prvok je OKNO s dvoma stranami: lava a prava. MQTT a UI kontrakt maju
pouzivat `window`, nie `cover`.

## Batch 1 - PWM HW test bez dorazov

DONE 2026-07-11:

- ESP firmware premenovany na `esp32_mqtt_window_controller`.
- MQTT topicy zmenene na:
  - `room1/window/left`
  - `room1/window/right`
  - `room1/window/STOP`
  - `room1/STOP`
- Device status topic: `devices/Room1_Window_Ctrl/status`.
- Samostatny RPi heartbeat sa nepouziva. Bezpecnost teraz stoji na MQTT loss
  stop, retained online/offline statuse, will message a `NO_COMMAND_TIMEOUT`.
- Default test konfiguracia ma `endstopsEnabled = false` pre obe strany.
- Default test rychlost je `30 %`.
- Default test `maxMoveMs = 5000`, aby PWM nezostal zapnuty dlho pri merani.
- Prikazy podporovane firmware:
  - `OPEN`
  - `OPEN:<speed>`
  - `CLOSE`
  - `CLOSE:<speed>`
  - `SPEED:<speed>`
  - `STOP` / `OFF`
- Backend podporuje `windows` v `devices.json` a runtime state store rozumie
  stavom `OPENING`, `CLOSING`, `OPEN`, `CLOSED`, `STOPPED`, `UNKNOWN`, `ERROR`.
- Web UI ma samostatne Window karty v Commands view a window polozky v Scene
  Editor palete.

### Ocakavany PWM smoke test

1. Flashnut firmware `esp32/devices/lan/ArduinoIDE/esp32_mqtt_window_controller`.
2. Nechat RPi backend a MQTT broker zapnuty.
3. Subscribe:
   ```bash
   mosquitto_sub -h 127.0.0.1 -t 'room1/#' -v
   ```
4. Poslat test lavej strany:
   ```bash
   mosquitto_pub -h 127.0.0.1 -t 'room1/window/left' -m 'OPEN:30'
   ```
5. Merat PWM na CH1. Po 5 sekundach ma prist timeout a PWM ma padnut na 0.
6. Poslat test opacneho smeru:
   ```bash
   mosquitto_pub -h 127.0.0.1 -t 'room1/window/left' -m 'CLOSE:30'
   ```
7. Merat PWM na CH2.
8. Zopakovat pre pravu stranu:
   - `room1/window/right OPEN:30` -> CH3
   - `room1/window/right CLOSE:30` -> CH4
9. Overit STOP:
   ```bash
   mosquitto_pub -h 127.0.0.1 -t 'room1/window/STOP' -m 'STOP'
   ```

## Batch 2 - test s H-mostikmi bez mechaniky

- Pripojit H-mostiky bez realneho okna alebo s odpojenou mechanickou zatazou.
- Overit smerovanie:
  - `OPEN` fyzicky znamena otvaranie danej strany.
  - `CLOSE` fyzicky znamena zatvaranie danej strany.
- Ak je smer opacny, prehodit motorove vodice alebo PWM channel mapping.
- Otestovat `SPEED:20`, `SPEED:50`, `SPEED:80` pocas pohybu.
- Overit, ze pri zmene OPEN -> CLOSE firmware najprv vynuluje opacny kanal.

## Batch 3 - dorazy a produkcna bezpecnost

- Osadit dorazy pre lavu/pravu stranu:
  - lava OPEN
  - lava CLOSED
  - prava OPEN
  - prava CLOSED
- Rozhodnut NC/NO; odporucane NC.
- V `config.cpp` prepnout `endstopsEnabled = true`.
- Namerat realnu dobu prejazdu a nastavit `maxMoveMs` s rezervou.
- Overit:
  - odmietnutie pohybu proti aktivnemu dorazu,
  - okamzity stop pri doraze,
  - timeout pri chybajucom doraze,
  - MQTT disconnect stop,
  - OTA safe stop,
  - globalny STOP.

## Batch 4 - finalne UI/sceny/docs

- Doplnenie scen s `window/left` a `window/right` akciami.
- Upravene produkcne texty a dokumentacia:
  - `docs/04_mqtt_protocol.md`
  - `docs/05_esp32_hardware_reference.md`
  - `docs/09_dashboard_api.md`
  - `docs/12_physical_installation.md`
- Pridat testy pre `/api/devices` validaciu s `windows`-only configom.
- Arduino IDE compile + realny HW protokol z merania.
