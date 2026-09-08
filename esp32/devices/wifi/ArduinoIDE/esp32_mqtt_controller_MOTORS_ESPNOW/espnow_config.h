#pragma once

#include <MuseumEspNowRadio.h>

#if __has_include("espnow_local.h")
#include "espnow_local.h"
#endif

#ifndef ESPNOW_ENABLED
#define ESPNOW_ENABLED 1
#endif
#ifndef MOTOR_DIRECT_MQTT_COMMANDS_ENABLED
#define MOTOR_DIRECT_MQTT_COMMANDS_ENABLED (!ESPNOW_ENABLED)
#endif
#if ESPNOW_ENABLED == MOTOR_DIRECT_MQTT_COMMANDS_ENABLED
#error "Select exactly one motor transport: ESP-NOW or direct MQTT"
#endif
#ifndef ESPNOW_CHANNEL
#define ESPNOW_CHANNEL 6
#endif
#ifndef ESPNOW_SELF_NODE
#define ESPNOW_SELF_NODE 2
#endif
#ifndef ESPNOW_MASTER_NODE
#define ESPNOW_MASTER_NODE 1
#endif
#ifndef ESPNOW_MASTER_MAC
#define ESPNOW_MASTER_MAC {0, 0, 0, 0, 0, 0}
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

extern const museum::RadioPeer ESPNOW_MASTER_PEER[1];
extern const uint8_t ESPNOW_PMK[16];
extern const museum::Timing ESPNOW_TIMING;
