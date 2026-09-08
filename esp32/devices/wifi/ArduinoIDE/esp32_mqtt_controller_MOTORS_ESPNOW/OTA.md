# OTA Update

OTA updates are enabled when `OTA_ENABLED` is true and the device is connected
to the same WiFi network as the development machine.

## Arduino IDE Upload

1. Open the motor controller sketch in Arduino IDE.
2. Select the network port for `ESP32-Museum-Room1`.
3. Start the upload.

Default OTA settings:

- `OTA_HOSTNAME = "ESP32-Museum-Room1"`
- `OTA_PASSWORD = "room1"`

## Update Behavior

- Motor outputs are disabled before the firmware upload starts.
- The watchdog is disabled during flash writes.
- A successful upload reboots the controller.
- A failed upload restores watchdog protection.

## Post-Update Checks

- The controller reconnects to WiFi.
- The status topic publishes `online`.
- The controller responds to `room1/motor1` and `room1/motor2`.
