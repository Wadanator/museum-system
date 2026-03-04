# OTA – `esp32_mqtt_button`

---

## 1) Predpoklady

- na zariadení už beží firmware s OTA podporou,
- `OTA_ENABLED = true`,
- ESP32 a vývojový PC sú v rovnakej sieti.

---

## 2) Upload postup

1. Otvor projekt v Arduino IDE.
2. Tools -> Port -> vyber network port podľa hostname.
3. Upload (`Ctrl+U`).

Aktuálne defaulty v kóde:
- `OTA_HOSTNAME = "ESP32-Room1-Trigger"`
- `OTA_PASSWORD = "room1"`

---

## 3) Troubleshooting

- port sa nezobrazuje -> skontroluj WiFi + hostname + firewall,
- timeout počas uploadu -> skús power cycle zariadenia,
- zlé heslo -> skontroluj `OTA_PASSWORD`.

---

## 4) Bezpečnostná poznámka

Pred produkciou zváž zmenu default OTA hesla.
