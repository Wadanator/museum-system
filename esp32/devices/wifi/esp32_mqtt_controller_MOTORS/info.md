# ESP32 MQTT Motors (`esp32_mqtt_controller_MOTORS`)

## Úloha

Ovládanie 2 motorov cez MQTT (`motor1`, `motor2`) + STOP.

## Subscribe topics

- `room1/motor1`
- `room1/motor2`
- `room1/STOP`

## Feedback + status

- Feedback: `<command_topic>/feedback` (`OK` / `ERROR`)
- Status: `devices/Room1_ESP_Motory/status` (`online` retained + LWT `offline`)

## Podporované príkazy

- `ON:<speed>:<direction>`
- `ON:<speed>:<direction>:<rampTime>`
- `OFF`
- `SPEED:<value>`
- `DIR:<value>`

## Konfigurácia

V `config.cpp` uprav:
- WiFi/MQTT
- `BASE_TOPIC_PREFIX`
- pin mapping motorov
- OTA hostname/password
