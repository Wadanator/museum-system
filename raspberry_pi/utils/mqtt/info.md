# `raspberry_pi/utils/mqtt` – Detailed Overview

---

## 1) Files and Responsibilities

- `mqtt_client.py`

  - Wrapper around the paho MQTT client
  - Connect/reconnect retry logic
  - Subscribe/publish API
  - Callback hooks for connection loss and restoration

- `mqtt_message_handler.py`

  - Central routing of incoming messages
  - Dispatches to:
    - Device registry
    - Feedback tracker
    - Scene trigger callbacks
    - Scene parser events

- `mqtt_feedback_tracker.py`

  - Pairs published commands with `/feedback` responses
  - Timeout and cleanup logic

- `mqtt_device_registry.py`

  - Manages device state based on `devices/<id>/status` messages
  - Stale device cleanup based on timeout

- `topic_rules.py`

  - Centralized topic patterns and helpers for subscribe/routing/feedback

---

## 2) Subscription Model (`mqtt_client.py`)

On connection, the client subscribes to the following topics
(generated via `MQTTRoomTopics.subscriptions()`):

- `devices/+/status`
- `<room_id>/+/feedback`
- `<room_id>/scene`
- `<room_id>/#`

Note:

- `room_id` is read from the config file (`[Room] room_id`).

---

## 3) Incoming Message Routing (`mqtt_message_handler.py`)

Routing priority order:

1. `devices/<id>/status` → `device_registry.update_device_status(...)`
2. `.../feedback` → `feedback_tracker.handle_feedback_message(...)`
3. `.../scene` + `START` → `button_callback()`
4. `.../start_scene` → `named_scene_callback(scene_name)`
5. Everything else → `scene_parser.register_mqtt_event(topic, payload)`

The final step is important for `mqttMessage` transitions in scenes.

---

## 5) Publish Flow and Feedback Tracking

`MQTTClient.publish(...)`:

- Publishes the payload.
- On success, optionally calls the tracker (`track_published_message`).

This means feedback tracking is coupled to publishing via the backend
`MQTTClient` wrapper.