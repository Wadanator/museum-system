#include "config.h"

// =============================================================================
// HARDWARE CONFIGURATION
// =============================================================================

bool USE_RELAY_MODULE = true;

// I2C configuration for the relay expander / RTC bus on Waveshare board.
int I2C_SDA_PIN = 42;
int I2C_SCL_PIN = 41;
int I2C_EXPANDER_ADDR = 0x20;

// Waveshare ESP32-S3 onboard NeoPixel.
int RGB_LED_PIN = 38;

// W5500 Ethernet chip pins on Waveshare ESP32-S3-POE-ETH-8DI-8RO.
// Source: Waveshare wiki port description.
int ETH_SPI_SCK_PIN = 15;
int ETH_SPI_MISO_PIN = 14;
int ETH_SPI_MOSI_PIN = 13;
int ETH_PHY_CS_PIN = 16;
int ETH_PHY_IRQ_PIN = 12;
int ETH_PHY_RST_PIN = 39;
int ETH_PHY_ADDR = 1;

// =============================================================================
// DEVICE DEFINITIONS
// =============================================================================

const Device DEVICES[] = {
  // Topic name            Pin/Bit   Inverted  AutoOff(ms)
  {"power/smoke_ON",       0,        false,    0},
  {"light/fire",           1,        false,    0},
  {"light/1",              2,        false,    0},
  {"effect/smoke",         3,        false,    12000},
  {"light/2",              4,        false,    0},
  {"light/3",              5,        false,    0},
  {"light/4",              6,        false,    0},
  {"light/5",              7,        false,    0}
};

const int DEVICE_COUNT = sizeof(DEVICES) / sizeof(Device);

// =============================================================================
// SYSTEM CONFIGURATION
// =============================================================================

bool DEBUG = false;

// MQTT
const char* MQTT_SERVER = "192.168.0.127";
int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "Room1_Relays_Ctrl";

// Connection Management
unsigned long NETWORK_CONNECT_TIMEOUT = 15000;
unsigned long NETWORK_RETRY_INTERVAL = 3000;
unsigned long MQTT_RETRY_INTERVAL = 2000;
unsigned long MAX_RETRY_INTERVAL = 30000;
unsigned long STATUS_PUBLISH_INTERVAL = 5000;
unsigned long CONNECTION_CHECK_INTERVAL = 5000;
int MAX_NETWORK_ATTEMPTS = 10;
int MAX_MQTT_ATTEMPTS = 10;
int MQTT_KEEP_ALIVE = 5;

// Inactivity timeout
unsigned long NO_COMMAND_TIMEOUT = 180000;

// Watchdog Timer
unsigned long WDT_TIMEOUT = 30;

// OTA Configuration
const char* OTA_HOSTNAME = "ESP32-RelayModule-Room1-LAN";
const char* OTA_PASSWORD = "room1";
bool OTA_ENABLED = true;
