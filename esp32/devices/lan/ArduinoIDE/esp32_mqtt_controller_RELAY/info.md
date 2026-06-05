# ESP32 LAN MQTT Relay Controller

Firmware for the Waveshare ESP32-S3 PoE/LAN relay module with W5500 Ethernet
as the primary transport and WiFi as a fallback transport.

## Network Behavior

- LAN is the preferred transport.
- WiFi fallback starts when LAN does not provide an active link/IP within the
  configured grace period.
- MQTT reconnects when the active transport changes.
- The MQTT client ID is `Room1_Relays_Ctrl`.
- Relay outputs are de-energized after sustained MQTT loss, using
  `NETWORK_FAILOVER_GRACE` to tolerate short LAN/WiFi transitions.

## Ethernet Hardware

The Waveshare module uses a W5500 Ethernet chip over SPI.

Used pins:

- `GPIO12` - ETH_INT
- `GPIO13` - ETH_MOSI
- `GPIO14` - ETH_MISO
- `GPIO15` - ETH_SCLK
- `GPIO16` - ETH_CS
- `GPIO39` - ETH_RST

The hardware and timing configuration is in `config.cpp`.

## Arduino IDE Requirements

- ESP32 Arduino core 3.x or newer.
- Board: `ESP32S3 Dev Module`.
- USB CDC setting according to the board upload/debug configuration.

## MQTT Interface

- broker: `192.168.0.127`
- base topic: `room1/`
- status topic: `devices/Room1_Relays_Ctrl/status`
- feedback topic format: `<command_topic>/feedback`

Subscribed command topics:

- `room1/<device_name>`
- `room1/effects/#`
- `room1/STOP`

Device payloads:

- `ON`
- `OFF`
- `1`
- `0`

Effect payloads:

- `ON`
- `OFF`
- `START`
- `STOP`
- `1`
- `0`

## Device Names

- `power/smoke_ON`
- `light/fire`
- `light/1`
- `effect/smoke`
- `light/2`
- `light/3`
- `light/4`
- `light/5`

## Effects

- `room1/effects/group1`
- `room1/effects/alone`
