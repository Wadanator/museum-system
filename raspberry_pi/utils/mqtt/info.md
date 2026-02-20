# `raspberry_pi/utils/mqtt` – aktuálna dokumentácia

## Súbory

- `mqtt_client.py` – connect/reconnect, subscribe, publish.
- `mqtt_message_handler.py` – routing incoming správ.
- `mqtt_device_registry.py` – online/offline stav zariadení.
- `mqtt_feedback_tracker.py` – párovanie publish -> feedback.
- `mqtt_contract.py` – validácia topic/payload pri publish.

## Subscription model

Po pripojení klient subscribuje:
- `devices/+/status`
- `<room_id>/+/feedback`
- `<room_id>/scene`
- `<room_id>/#`

## Routing model (`mqtt_message_handler.py`)

Poradie:
1. device status (`devices/<id>/status`)
2. feedback (`.../feedback`)
3. button trigger (`.../scene` + `START`)
4. named scene (`.../start_scene`)
5. všetko ostatné ide do SceneParser ako MQTT event pre transitions.

## Poznámka

Feedback tracker funguje len pre správy publishované cez backendový `MQTTClient.publish()`.
