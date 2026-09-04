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

// Waveshare onboard RS485. DE/RE direction control is confirmed on GPIO21 for
// this board/wiring.
int RS485_TX_PIN = 17;
int RS485_RX_PIN = 18;
int RS485_DE_PIN = 21;
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
const char* WIFI_SSID = "kastielhome";
const char* WIFI_PASSWORD = "Kastiel18";

const unsigned long WINDOW_TEST_MAX_OPEN_MOVE_MS = 6500;
const unsigned long WINDOW_TEST_MAX_CLOSE_MOVE_MS = 10000;
const unsigned long WINDOW_PROD_MAX_OPEN_MOVE_MS = 6500;
const unsigned long WINDOW_PROD_MAX_CLOSE_MOVE_MS = 10000;
const bool WINDOW_TEST_OPEN_ENDSTOP_ENABLED = false;
const bool WINDOW_TEST_CLOSE_ENDSTOP_ENABLED = false;
const bool WINDOW_PROD_OPEN_ENDSTOP_ENABLED = false;
const bool WINDOW_PROD_CLOSE_ENDSTOP_ENABLED = true;
const unsigned long WINDOW_LEFT_CLOSE_ENDSTOP_PRESS_MS = 3000;
const unsigned long WINDOW_RIGHT_CLOSE_ENDSTOP_PRESS_MS = 2000;
const unsigned long WINDOW_AUX_CLOSE_ENDSTOP_PRESS_MS = 2000;

#if WINDOW_ACTIVE_PROFILE == WINDOW_PROFILE_PROD_WITH_ENDSTOPS
const bool WINDOW_ACTIVE_OPEN_ENDSTOP_ENABLED = WINDOW_PROD_OPEN_ENDSTOP_ENABLED;
const bool WINDOW_ACTIVE_CLOSE_ENDSTOP_ENABLED = WINDOW_PROD_CLOSE_ENDSTOP_ENABLED;
const unsigned long WINDOW_ACTIVE_MAX_OPEN_MOVE_MS = WINDOW_PROD_MAX_OPEN_MOVE_MS;
const unsigned long WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS = WINDOW_PROD_MAX_CLOSE_MOVE_MS;
#else
const bool WINDOW_ACTIVE_OPEN_ENDSTOP_ENABLED = WINDOW_TEST_OPEN_ENDSTOP_ENABLED;
const bool WINDOW_ACTIVE_CLOSE_ENDSTOP_ENABLED = WINDOW_TEST_CLOSE_ENDSTOP_ENABLED;
const unsigned long WINDOW_ACTIVE_MAX_OPEN_MOVE_MS = WINDOW_TEST_MAX_OPEN_MOVE_MS;
const unsigned long WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS = WINDOW_TEST_MAX_CLOSE_MOVE_MS;
#endif

const bool WINDOW_ACTIVE_ENDSTOPS_ENABLED =
  WINDOW_ACTIVE_OPEN_ENDSTOP_ENABLED || WINDOW_ACTIVE_CLOSE_ENDSTOP_ENABLED;

const unsigned long WINDOW_ACTIVE_MAX_MOVE_MS =
  WINDOW_ACTIVE_MAX_OPEN_MOVE_MS > WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS
    ? WINDOW_ACTIVE_MAX_OPEN_MOVE_MS
    : WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS;

// Two active window sides. Each side uses two PWM channels: one for OPEN and
// one for CLOSE. The active profile enables the tested DI1-DI4 end-stops and
// every movement still has a local hard timeout configured above.
//
// Waveshare Industrial ESP32-S3 Control Board With 8-Channel Digital Input &
// Output: the DI terminal labels map directly to ESP32 GPIO pins here.
// These DI/D inputs are ONLY end-stop inputs. They are not the PWM outputs;
// PWM is written to the external Modbus RTU PWM module over RS485.
//
// End-stop terminal assignment:
//   DI1 / D1 / GPIO4  = left window OPEN end-stop
//   DI2 / D2 / GPIO5  = left window CLOSE end-stop
//   DI3 / D3 / GPIO6  = right window OPEN end-stop
//   DI4 / D4 / GPIO7  = right window CLOSE end-stop
//   DI5 / D5 / GPIO8  = local scene START trigger button
const int DI1_LEFT_OPEN_ENDSTOP_PIN = 4;
const int DI2_LEFT_CLOSE_ENDSTOP_PIN = 5;
const int DI3_RIGHT_OPEN_ENDSTOP_PIN = 6;
const int DI4_RIGHT_CLOSE_ENDSTOP_PIN = 7;
const int DI5_SCENE_TRIGGER_BUTTON_PIN = 8;
const int UNUSED_ENDSTOP_PIN = -1;
const uint8_t WINDOW_DEFAULT_SPEED_PERCENT = 30;

const WindowSideConfig WINDOW_SIDES[] = {
  // On     Topic           Label                OPEN CH                CLOSE CH               OPEN DI                     CLOSE DI                     OPEN stop                         CLOSE stop                        NC/active-low   Speed                         Max OPEN ms                     Max CLOSE ms                      CLOSE press ms
  {true,    "window/left",  "Window left side",  WINDOW_PWM_CH1,        WINDOW_PWM_CH2,        DI1_LEFT_OPEN_ENDSTOP_PIN,  DI2_LEFT_CLOSE_ENDSTOP_PIN,  WINDOW_ACTIVE_OPEN_ENDSTOP_ENABLED, WINDOW_ACTIVE_CLOSE_ENDSTOP_ENABLED, true, WINDOW_DEFAULT_SPEED_PERCENT, WINDOW_ACTIVE_MAX_OPEN_MOVE_MS, WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS, WINDOW_LEFT_CLOSE_ENDSTOP_PRESS_MS},
  {true,    "window/right", "Window right side", WINDOW_PWM_CH4,        WINDOW_PWM_CH3,        DI3_RIGHT_OPEN_ENDSTOP_PIN, DI4_RIGHT_CLOSE_ENDSTOP_PIN, WINDOW_ACTIVE_OPEN_ENDSTOP_ENABLED, WINDOW_ACTIVE_CLOSE_ENDSTOP_ENABLED, true, WINDOW_DEFAULT_SPEED_PERCENT, WINDOW_ACTIVE_MAX_OPEN_MOVE_MS, WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS, WINDOW_RIGHT_CLOSE_ENDSTOP_PRESS_MS},
  {false,   "window/aux1",  "Window aux 1",     WINDOW_PWM_UNUSED_CH5, WINDOW_PWM_UNUSED_CH6,  UNUSED_ENDSTOP_PIN,         UNUSED_ENDSTOP_PIN,          false, false, true, WINDOW_DEFAULT_SPEED_PERCENT, WINDOW_ACTIVE_MAX_OPEN_MOVE_MS, WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS, WINDOW_AUX_CLOSE_ENDSTOP_PRESS_MS},
  {false,   "window/aux2",  "Window aux 2",     WINDOW_PWM_UNUSED_CH7, WINDOW_PWM_UNUSED_CH8,  UNUSED_ENDSTOP_PIN,         UNUSED_ENDSTOP_PIN,          false, false, true, WINDOW_DEFAULT_SPEED_PERCENT, WINDOW_ACTIVE_MAX_OPEN_MOVE_MS, WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS, WINDOW_AUX_CLOSE_ENDSTOP_PRESS_MS}
};

const int WINDOW_SIDE_COUNT = sizeof(WINDOW_SIDES) / sizeof(WindowSideConfig);

// Digital input mode for Waveshare isolated DI pins. Change to INPUT_PULLUP
// only if the end-stops are wired directly to ESP32 GPIO instead of the DI port.
int ENDSTOP_INPUT_MODE = INPUT;
unsigned long ENDSTOP_POLL_INTERVAL_MS = 50;
unsigned long DIRECTION_CHANGE_DEADTIME_MS = 350;

// Optional local scene START trigger on DI5. It publishes the same MQTT command
// as the standalone ESPHome trigger button.
bool SCENE_TRIGGER_BUTTON_ENABLED = true;
int SCENE_TRIGGER_BUTTON_PIN = DI5_SCENE_TRIGGER_BUTTON_PIN;
int SCENE_TRIGGER_BUTTON_INPUT_MODE = INPUT;
bool SCENE_TRIGGER_BUTTON_ACTIVE_LOW = true;
unsigned long SCENE_TRIGGER_DEBOUNCE_MS = 100;
unsigned long SCENE_TRIGGER_COOLDOWN_MS = 4000;
const char* SCENE_TRIGGER_TOPIC_NAME = "scene";
const char* SCENE_TRIGGER_PAYLOAD = "START";

// System configuration.
bool DEBUG = true;

// MQTT broker and topic configuration.
// Use the Raspberry Pi's fixed address instead of mDNS for more reliable WiFi fallback.
const char* MQTT_SERVER = "192.168.0.127";
int MQTT_PORT = 1883;
const char* BASE_TOPIC_PREFIX = "room1/";
const char* CLIENT_ID = "Room1_Window_Ctrl";

// Connection management.
unsigned long NETWORK_CONNECT_TIMEOUT = 15000;
unsigned long LAN_PRIMARY_CONNECT_GRACE = 3000;
unsigned long NETWORK_FAILOVER_GRACE = 8000;
unsigned long WIFI_CONNECT_STALL_TIMEOUT_MS = 15000;
unsigned long NETWORK_RETRY_INTERVAL = 3000;
unsigned long MQTT_RETRY_INTERVAL = 2000;
unsigned long MAX_RETRY_INTERVAL = 30000;
unsigned long STATUS_PUBLISH_INTERVAL = 5000;
unsigned long CONNECTION_CHECK_INTERVAL = 5000;
int MAX_NETWORK_ATTEMPTS = 10;
int MAX_MQTT_ATTEMPTS = 10;
int MQTT_KEEP_ALIVE = 15;

// Stop active PWM if commands stop arriving for too long.
unsigned long NO_COMMAND_TIMEOUT = 180000;

// Watchdog timer. Keep this at 1.5x the longest active local movement timeout.
const unsigned long WDT_TIMEOUT_MS = (WINDOW_ACTIVE_MAX_MOVE_MS * 3UL) / 2UL;

// OTA configuration.
const char* OTA_HOSTNAME = "ESP32-Window-Room1-LAN";
const char* OTA_PASSWORD = "room1";
bool OTA_ENABLED = true;
