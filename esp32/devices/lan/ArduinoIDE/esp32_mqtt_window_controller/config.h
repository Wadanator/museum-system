#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

extern int RGB_LED_PIN;

// Waveshare W5500 Ethernet over SPI.
extern int ETH_SPI_SCK_PIN;
extern int ETH_SPI_MISO_PIN;
extern int ETH_SPI_MOSI_PIN;
extern int ETH_PHY_CS_PIN;
extern int ETH_PHY_IRQ_PIN;
extern int ETH_PHY_RST_PIN;
extern int ETH_PHY_ADDR;

// Onboard RS485 connected to the external 4-channel PWM Modbus RTU module.
extern int RS485_TX_PIN;
extern int RS485_RX_PIN;
extern int RS485_DE_PIN;
extern unsigned long RS485_BAUD_RATE;
extern uint32_t RS485_SERIAL_CONFIG;
extern uint8_t PWM_MODBUS_ID;
extern uint8_t PWM_CHANNEL_COUNT;
extern uint16_t PWM_REGISTER_BASE;
extern uint8_t PWM_CHANNEL_REGISTER_STRIDE;
extern uint8_t PWM_DUTY_REGISTER_OFFSET;
extern uint32_t PWM_FREQUENCY_HZ;
extern uint16_t PWM_DUTY_OFF;
extern uint16_t PWM_DUTY_MAX;

// WiFi fallback.
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// Window side motor definitions.
#define WINDOW_PROFILE_TEST_NO_ENDSTOPS_SAFE 1
#define WINDOW_PROFILE_PROD_WITH_ENDSTOPS 2

#ifndef WINDOW_ACTIVE_PROFILE
#define WINDOW_ACTIVE_PROFILE WINDOW_PROFILE_PROD_WITH_ENDSTOPS
#endif

extern const unsigned long WINDOW_TEST_MAX_OPEN_MOVE_MS;
extern const unsigned long WINDOW_TEST_MAX_CLOSE_MOVE_MS;
extern const unsigned long WINDOW_PROD_MAX_OPEN_MOVE_MS;
extern const unsigned long WINDOW_PROD_MAX_CLOSE_MOVE_MS;
extern const bool WINDOW_ACTIVE_OPEN_ENDSTOP_ENABLED;
extern const bool WINDOW_ACTIVE_CLOSE_ENDSTOP_ENABLED;
extern const bool WINDOW_ACTIVE_ENDSTOPS_ENABLED;
extern const unsigned long WINDOW_ACTIVE_MAX_OPEN_MOVE_MS;
extern const unsigned long WINDOW_ACTIVE_MAX_CLOSE_MOVE_MS;
extern const unsigned long WINDOW_ACTIVE_MAX_MOVE_MS;
extern const unsigned long WINDOW_LEFT_CLOSE_ENDSTOP_PRESS_MS;
extern const unsigned long WINDOW_RIGHT_CLOSE_ENDSTOP_PRESS_MS;
extern const unsigned long WINDOW_AUX_CLOSE_ENDSTOP_PRESS_MS;

enum WindowPwmChannel {
  WINDOW_PWM_CH1 = 0,
  WINDOW_PWM_CH2 = 1,
  WINDOW_PWM_CH3 = 2,
  WINDOW_PWM_CH4 = 3,
  WINDOW_PWM_UNUSED_CH5 = 4,
  WINDOW_PWM_UNUSED_CH6 = 5,
  WINDOW_PWM_UNUSED_CH7 = 6,
  WINDOW_PWM_UNUSED_CH8 = 7
};

struct WindowSideConfig {
  bool enabled;
  const char* topicName;
  const char* displayName;
  uint8_t pwmOpenChannel;
  uint8_t pwmCloseChannel;
  int openEndstopPin;
  int closeEndstopPin;
  bool openEndstopEnabled;
  bool closeEndstopEnabled;
  bool endstopActiveLow;
  uint8_t defaultSpeed;
  unsigned long maxOpenMoveMs;
  unsigned long maxCloseMoveMs;
  unsigned long closeEndstopPressMs;
};

extern const WindowSideConfig WINDOW_SIDES[];
extern const int WINDOW_SIDE_COUNT;
extern int ENDSTOP_INPUT_MODE;
extern unsigned long ENDSTOP_POLL_INTERVAL_MS;
extern unsigned long DIRECTION_CHANGE_DEADTIME_MS;

// System configuration.
extern bool DEBUG;

// MQTT broker and topic configuration.
extern const char* MQTT_SERVER;
extern int MQTT_PORT;
extern const char* BASE_TOPIC_PREFIX;
extern const char* CLIENT_ID;

// Connection management.
extern unsigned long NETWORK_CONNECT_TIMEOUT;
extern unsigned long LAN_PRIMARY_CONNECT_GRACE;
extern unsigned long NETWORK_FAILOVER_GRACE;
extern unsigned long WIFI_CONNECT_STALL_TIMEOUT_MS;
extern unsigned long NETWORK_RETRY_INTERVAL;
extern unsigned long MQTT_RETRY_INTERVAL;
extern unsigned long MAX_RETRY_INTERVAL;
extern unsigned long STATUS_PUBLISH_INTERVAL;
extern unsigned long CONNECTION_CHECK_INTERVAL;
extern int MAX_NETWORK_ATTEMPTS;
extern int MAX_MQTT_ATTEMPTS;
extern int MQTT_KEEP_ALIVE;

// Safety timeouts.
extern unsigned long NO_COMMAND_TIMEOUT;

// Watchdog timer.
extern const unsigned long WDT_TIMEOUT_MS;

// OTA configuration.
extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern bool OTA_ENABLED;

#endif
