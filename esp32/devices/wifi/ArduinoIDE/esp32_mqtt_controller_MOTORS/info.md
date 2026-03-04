# ESP32 MQTT Motors (`esp32_mqtt_controller_MOTORS`)

Firmware pre riadenie dvoch motorov cez MQTT.

---

## 1) Zodpovednosť modulu

- subscribe motor command topics,
- parse motor command payload,
- ovládanie motor driver pinov/PWM,
- feedback publish na `<topic>/feedback`,
- pravidelný status publish.

---

## 2) MQTT topics

Subscribe:
- `room1/motor1`
- `room1/motor2`
- `room1/STOP`

Status:
- `devices/Room1_ESP_Motory/status` (`online` retained + LWT `offline`)

Feedback:
- `<command_topic>/feedback` (`OK`/`ERROR`)

---

## 3) Podporované payloady

Parser podporuje:
- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTime>`
- `OFF`
- `SPEED:<value>`
- `DIR:<value>`

Príklady:
- `room1/motor1` -> `ON:150:L`
- `room1/motor2` -> `ON:90:R:4000`
- `room1/motor1` -> `SPEED:200`
- `room1/motor2` -> `OFF`

---

## 4) STOP command

`room1/STOP` vyvolá okamžité vypnutie motorov (`turnOffHardware`).
Používa sa pri ukončení scény alebo emergency stop.

---

## 5) Konfigurácia (`config.cpp`)

Uprav minimálne:
- WiFi/MQTT nastavenia,
- `BASE_TOPIC_PREFIX`,
- `CLIENT_ID`,
- motor pin mapping,
- PWM parametre,
- OTA hostname/password.

---

## 6) Prevádzkové poznámky

- Pri zmene room prefixu musí sedieť s Pi backend `room_id`.
- Feedback topic je odvodený z command topicu + `/feedback`.
- Pri strate MQTT sa spoliehaš na reconnect mechanizmus firmvéru.
