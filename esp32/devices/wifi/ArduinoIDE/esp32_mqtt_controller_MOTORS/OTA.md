# OTA – `esp32_mqtt_controller_MOTORS`

---

## 1) Predpoklady

- firmware má zapnuté OTA (`OTA_ENABLED = true`),
- zariadenie je online v rovnakej sieti ako vývojový stroj.

---

## 2) Upload

1. Otvor projekt v Arduino IDE.
2. Vyber network port zariadenia (hostname).
3. Upload (`Ctrl+U`).

Aktuálne defaulty:
- `OTA_HOSTNAME = "ESP32-Museum-Room1"`
- `OTA_PASSWORD = "room1"`

---

## 3) Po update over

- zariadenie sa znovu pripojí do WiFi,
- publikuje `online` na status topic,
- reaguje na `room1/motor1` / `room1/motor2`.
