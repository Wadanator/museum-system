#include "config.h"

// Waveshare ESP32-S3 onboard NeoPixel.
int RGB_LED_PIN = 38;

// W5500 Ethernet chip pins on Waveshare ESP32-S3-POE-ETH-8DI-8RO.
int ETH_SPI_SCK_PIN = 15;
int ETH_SPI_MISO_PIN = 14;
int ETH_SPI_MOSI_PIN = 13;
int ETH_PHY_CS_PIN = 16;
int ETH_PHY_IRQ_PIN = 12;
int ETH_PHY_RST_PIN = 39;
int ETH_PHY_ADDR = 1;

// Waveshare onboard RS485. The public Waveshare pin table lists TX/RX only;
// keep DE disabled unless the physical board/manual confirms a direction pin.
int RS485_TX_PIN = 17;
int RS485_RX_PIN = 18;
int RS485_DE_PIN = -1;
unsigned long RS485_BAUD_RATE = 9600;
uint32_t RS485_SERIAL_CONFIG = SERIAL_8N1;
uint8_t PWM_MODBUS_ID = 1;
uint8_t PWM_CHANNEL_COUNT = 4;

// Waveshare Modbus RTU PWM Output 4CH maps each channel as:
// frequency high word, frequency low word, duty. Duty registers are therefore
// CH1=0x0002, CH2=0x0005, CH3=0x0008, CH4=0x000B.
uint16_t PWM_REGISTER_BASE = 0x0000;
uint8_t PWM_CHANNEL_REGISTER_STRIDE = 3;
uint8_t PWM_DUTY_REGISTER_OFFSET = 2;
uint32_t PWM_FREQUENCY_HZ = 20000;
uint16_t PWM_DUTY_OFF = 0;
uint16_t PWM_DUTY_MAX = 10000;

// WiFi fallback. LAN remains primary; WiFi is used only when LAN is down.
const char* WIFI_SSID = "Museum-Room1";
const char* WIFI_PASSWORD = "88888888";

// Two active window sides. Each side uses two PWM channels: one for OPEN and
// one for CLOSE. TEST DEFAULT: end-stops are disabled so PWM can be measured
// before the limit switches are installed. Enable them for production.
const WindowSideConfig WINDOW_SIDES[] = {
  // On     Topic           Label                OPEN CH  CLOSE CH  OPEN DI  CLOSE DI  Endstops  NC/active-low  Speed  Max move
  {true,    "window/left",  "Window left side",  0,       1,        4,       5,        false,    true,          30,    5000},
  {true,    "window/right", "Window right side", 2,       3,        6,       7,        false,    true,          30,    5000},
  {false,   "window/aux1",  "Window aux 1",     4,       5,        8,       9,        false,    true,          30,    5000},
  {false,   "window/aux2",  "Window aux 2",     6,       7,        10,      11,       false,    true,          30,    5000}
};

const int WINDOW_SIDE_COUNT = sizeof(WINDOW_SIDES) / sizeof(WindowSideConfig);

// Digital input mode for Waveshare isolated DI pins. Change to INPUT_PULLUP
// only if the end-stops are wired directly to ESP32 GPIO instead of the DI port.
int ENDSTOP_INPUT_MODE = INPUT;
unsigned long ENDSTOP_POLL_INTERVAL_MS = 50;
unsigned long DIRECTION_CHANGE_DEADTIME_MS = 350;

// System configuration.
bool DEBUG = true;

// MQTT broker and topic configuration.
const char* MQTT_SERVER = "TechMuzeumRoom1.local";
int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "Room1_Window_Ctrl";

// Connection management.
unsigned long NETWORK_CONNECT_TIMEOUT = 15000;
unsigned long LAN_PRIMARY_CONNECT_GRACE = 3000;
unsigned long NETWORK_FAILOVER_GRACE = 5000;
unsigned long NETWORK_RETRY_INTERVAL = 3000;
unsigned long MQTT_RETRY_INTERVAL = 2000;
unsigned long MAX_RETRY_INTERVAL = 30000;
unsigned long STATUS_PUBLISH_INTERVAL = 5000;
unsigned long CONNECTION_CHECK_INTERVAL = 5000;
int MAX_NETWORK_ATTEMPTS = 10;
int MAX_MQTT_ATTEMPTS = 10;
int MQTT_KEEP_ALIVE = 5;

// Stop active PWM if commands stop arriving for too long.
unsigned long NO_COMMAND_TIMEOUT = 180000;

// Watchdog timer.
unsigned long WDT_TIMEOUT = 30;

// OTA configuration.
const char* OTA_HOSTNAME = "ESP32-Window-Room1-LAN";
const char* OTA_PASSWORD = "room1";
bool OTA_ENABLED = true;
