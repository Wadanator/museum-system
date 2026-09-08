#pragma once

#include <MuseumEspNowRadio.h>

#if __has_include("espnow_local.h")
#include "espnow_local.h"
#endif

#ifndef ESPNOW_ENABLED
#define ESPNOW_ENABLED 1
#endif
#ifndef RELAY_MOTOR_BRIDGE_ENABLED
#define RELAY_MOTOR_BRIDGE_ENABLED ESPNOW_ENABLED
#endif
#ifndef RELAY_WIFI_FALLBACK_ENABLED
#define RELAY_WIFI_FALLBACK_ENABLED 1
#endif
#if ESPNOW_ENABLED != RELAY_MOTOR_BRIDGE_ENABLED
#error "Relay ESP-NOW and motor bridge must be enabled or disabled together"
#endif
#ifndef ESPNOW_CHANNEL
#define ESPNOW_CHANNEL 6
#endif
#if ESPNOW_ENABLED && (ESPNOW_CHANNEL < 1 || ESPNOW_CHANNEL > 13)
#error "ESP-NOW requires a fixed 2.4 GHz channel from 1 to 13"
#endif
#ifndef RELAY_WIFI_CONNECT_TIMEOUT_MS
#define RELAY_WIFI_CONNECT_TIMEOUT_MS 8000UL
#endif
#if RELAY_WIFI_CONNECT_TIMEOUT_MS < 1000 || RELAY_WIFI_CONNECT_TIMEOUT_MS > 30000
#error "WiFi fallback connection timeout must be between 1000 and 30000 ms"
#endif
#ifndef ESPNOW_SELF_NODE
#define ESPNOW_SELF_NODE 1
#endif
#ifndef ESPNOW_MOTOR_NODE
#define ESPNOW_MOTOR_NODE 2
#endif
#ifndef ESPNOW_MOTOR_MAC
#define ESPNOW_MOTOR_MAC {0, 0, 0, 0, 0, 0}
#endif
#ifndef ESPNOW_ENCRYPTION_ENABLED
#define ESPNOW_ENCRYPTION_ENABLED 0
#endif
#ifndef ESPNOW_PMK_BYTES
#define ESPNOW_PMK_BYTES {0}
#endif
#ifndef ESPNOW_LMK_BYTES
#define ESPNOW_LMK_BYTES {0}
#endif

struct MotorRoute {
  const char* nodeId;
  const char* topics[2];  // Full MQTT command topics, not relay-local names.
};
extern const museum::RadioPeer ESPNOW_PEERS[];
extern const MotorRoute ESPNOW_ROUTES[];
extern const size_t ESPNOW_PEER_COUNT;
extern const uint8_t ESPNOW_PMK[16];
extern const museum::Timing ESPNOW_TIMING;
extern const uint32_t ESPNOW_PROXY_STATUS_INTERVAL_MS;
