#pragma once

// Use the motor's printed STA MAC, not its Bluetooth or Ethernet MAC.
#define ESPNOW_MOTOR_MAC {0, 0, 0, 0, 0, 0}
#define ESPNOW_SELF_NODE 1
#define ESPNOW_MOTOR_NODE 2
#define ESPNOW_CHANNEL 6
// The router's 2.4 GHz channel must match ESPNOW_CHANNEL on both ESPs.
#define RELAY_WIFI_FALLBACK_ENABLED 1
// Local-only, matching 16-byte keys on both devices when encryption is enabled.
// #define ESPNOW_ENCRYPTION_ENABLED 1
// #define ESPNOW_PMK_BYTES { ...16 bytes... }
// #define ESPNOW_LMK_BYTES { ...16 bytes... }
