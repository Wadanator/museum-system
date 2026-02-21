# `raspberry_pi/utils/mqtt` – detailný prehľad

---

## 1) Súbory a zodpovednosti

- `mqtt_client.py`

  - wrapper nad paho clientom
  - connect/reconnect retry logika
  - subscribe/publish API
  - callback hooky pri strate/obnove spojenia
- `mqtt_message_handler.py`

  - central routing incoming správ
  - dispatch do:
    - device registry
    - feedback tracker
    - scene trigger callbackov
    - scene parser eventov
- `mqtt_feedback_tracker.py`

  - páruje publishnuté commandy s `/feedback` odpoveďami
  - timeout/cleanup logika
- `mqtt_device_registry.py`

  - správa stavu zariadení podľa `devices/<id>/status`
  - stale cleanup podľa timeoutu

---

## 2) Subscription model (`mqtt_client.py`)

Po pripojení sa subscribuje:

- `devices/+/status`
- `<room_id>/+/feedback`
- `<room_id>/scene`
- `<room_id>/#`

Poznámka:

- `room_id` je z configu (`[Room] room_id`).

---

## 3) Incoming message routing (`mqtt_message_handler.py`)

Poradie routingu:

1. `devices/<id>/status` -> `device_registry.update_device_status(...)`
2. `.../feedback` -> `feedback_tracker.handle_feedback_message(...)`
3. `.../scene` + `START` -> `button_callback()`
4. `.../start_scene` -> `named_scene_callback(scene_name)`
5. všetko ostatné -> `scene_parser.register_mqtt_event(topic, payload)`

Tento posledný bod je dôležitý pre `mqttMessage` transitions v scénach.

---

## 5) Publish flow a feedback tracking

`MQTTClient.publish(...)`:

- publikuje payload,
- pri úspechu môže zavolať tracker (`track_published_message`).

To znamená, že feedback tracking je naviazaný na publish cez backendový MQTTClient wrapper
