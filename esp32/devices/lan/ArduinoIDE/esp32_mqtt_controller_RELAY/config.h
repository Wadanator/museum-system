#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Hardware configuration.
extern bool USE_RELAY_MODULE;

extern int I2C_SDA_PIN;
extern int I2C_SCL_PIN;
extern int I2C_EXPANDER_ADDR;

extern int RGB_LED_PIN;

// Waveshare W5500 Ethernet over SPI.
extern int ETH_SPI_SCK_PIN;
extern int ETH_SPI_MISO_PIN;
extern int ETH_SPI_MOSI_PIN;
extern int ETH_PHY_CS_PIN;
extern int ETH_PHY_IRQ_PIN;
extern int ETH_PHY_RST_PIN;
extern int ETH_PHY_ADDR;

// WiFi fallback.
extern const char* WIFI_SSID;
extern const char* WIFI_PASSWORD;

// Device definitions.
struct Device {
  const char* name;
  int pin;
  bool inverted;
  unsigned long autoOffMs;
};

extern const Device DEVICES[];
extern const int DEVICE_COUNT;

// System configuration.

// Diagnostic output.
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
extern unsigned long NETWORK_RETRY_INTERVAL;
extern unsigned long MQTT_RETRY_INTERVAL;
extern unsigned long MAX_RETRY_INTERVAL;
extern unsigned long STATUS_PUBLISH_INTERVAL;
extern unsigned long CONNECTION_CHECK_INTERVAL;
extern int MAX_NETWORK_ATTEMPTS;
extern int MAX_MQTT_ATTEMPTS;
extern int MQTT_KEEP_ALIVE;

// Inactivity safety timeout.
extern unsigned long NO_COMMAND_TIMEOUT;

// Watchdog timer.
extern unsigned long WDT_TIMEOUT;

// OTA configuration.
extern const char* OTA_HOSTNAME;
extern const char* OTA_PASSWORD;
extern bool OTA_ENABLED;

#endif
