# Architektúra systému (aktuálna implementácia)

Tento dokument popisuje runtime architektúru tak, ako je implementovaná v `raspberry_pi/` a `esp32/devices/wifi/`.

---

## 1) Runtime topológia

- **MQTT broker** je centrálna message bus.
- **Raspberry Pi controller** vykonáva scény a koordinuje media + device commands.
- **ESP32 nodes** vykonávajú fyzické akcie a vracajú status/feedback.

```text
Dashboard / Button / MQTT trigger
          |
          v
  Raspberry Pi MuseumController
          |
          v
      MQTT broker
      /        \
 ESP32 relay  ESP32 motors (+button publish trigger)
```

---

## 2) Raspberry Pi vrstva

## 2.1 Entry point a orchestrácia

- `raspberry_pi/main.py`
  - inicializácia runtime modulov
  - wiring callbackov
  - spúšťanie/zastavovanie scén
  - graceful cleanup

`MuseumController` štandardne:

1. načíta config,
2. inicializuje služby cez `ServiceContainer`,
3. prepojí MQTT handlery,
4. spustí web dashboard,
5. beží main loop (health checks + poll intervaly).

## 2.2 Service container

- `raspberry_pi/utils/service_container.py`
  - centrálne vytvára: audio/video handlers, MQTT client + pomocné služby, monitor, button handler.

## 2.3 Scene engine

- `utils/state_machine.py`
  - load/validate scene JSON,
  - drží current state + scene čas.
- `utils/scene_parser.py`
  - lifecycle scény,
  - forwarding eventov do transition managera,
  - dynamic audio preload (`sfx_` súbory).
- `utils/state_executor.py`
  - vykonáva akcie typov `mqtt`, `audio`, `video`.
- `utils/transition_manager.py`
  - transition typy:
    - `timeout`
    - `audioEnd`
    - `videoEnd`
    - `mqttMessage`
    - `always`

## 2.4 Media vrstva

- `utils/audio_handler.py`
  - `pygame` mixer,
  - RAM cache pre `sfx_...` súbory,
  - stream music + callback pri dohraní.
- `utils/video_handler.py`
  - `mpv` subprocess,
  - IPC socket commandy,
  - health-check + auto-restart pri chybe.

## 2.5 MQTT vrstva

- `utils/mqtt/mqtt_client.py`

  - connect/reconnect, subscribe, publish.
- `utils/mqtt/mqtt_message_handler.py`

  - route incoming messages podľa topic patternov.
- `utils/mqtt/mqtt_feedback_tracker.py`

  - track publish -> feedback timeout.
- `utils/mqtt/mqtt_device_registry.py`

  - online/offline registry device status topics.

## 2.6 Web vrstva

- `raspberry_pi/Web/`
  - Flask routes + Socket.IO eventy
  - ovládanie scény, media, commands, system actions
  - live status/logs pre operátora

---

## 3) MQTT subscriptions na Pi

Po úspešnom pripojení backend subscribuje minimálne:

- `devices/+/status`
- `<room_id>/+/feedback`
- `<room_id>/scene`
- `<room_id>/#`

To umožní:

- detekciu device online/offline,
- príjem feedbacku na príkazy,
- trigger default/named scene,
- prijímanie transition eventov.

---

## 4) ESP32 firmware komponenty v repozitári

## 4.1 `esp32_mqtt_button`

- publikuje trigger scény na `room1/scene` (`START`)
- publikuje status na `devices/Room1_ESP_Trigger/status`

## 4.2 `esp32_mqtt_controller_MOTORS`

- subscribuje `room1/motor1`, `room1/motor2`, `room1/STOP`
- spracúva payloady `ON:...`, `OFF`, `SPEED:...`, `DIR:...`
- publikuje `<topic>/feedback` + status topic

## 4.3 `esp32_mqtt_controller_RELAY`

- subscribuje `room1/<device_name>`, `room1/effects/#`, `room1/STOP`
- podpora I2C relay modulu aj direct GPIO režimu
- publikuje feedback/status

---

## 5) Scene JSON kontrakt (praktický prehľad)

Povinné root polia:

- `sceneId`
- `initialState`
- `states`

Voliteľné:

- `version`
- `description`
- `globalEvents`

V stave (`states.<name>`) sú podporované:

- `description`
- `onEnter` (array akcií)
- `timeline` (array časovaných akcií)
- `onExit` (array akcií)
- `transitions` (array prechodov)

Akcie:

- `{"action":"mqtt", ...}`
- `{"action":"audio", ...}`
- `{"action":"video", ...}`

---

## 6) Rozšírenie systému (odporúčaný postup)

Pri pridávaní nového zariadenia:

1. implementácia topic/payload v ESP32 (alebo inom subscriberi),
2. scene action + transition podľa potreby,
3. aktualizácia `docs/mqtt_topics.md` a zariadeniovej `info.md`.

Takto ostane dokumentácia aj runtime konzistentná.
