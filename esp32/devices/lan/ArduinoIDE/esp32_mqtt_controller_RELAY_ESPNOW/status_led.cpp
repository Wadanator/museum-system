#include "status_led.h"
#include "config.h"
#include "debug.h"

// Onboard WS2812 pin for the Waveshare relay board.
#define LED_PIN 38

// Maximum brightness (0-255). 50 is suitable for indoor diagnostics.
#define MAX_BRIGHTNESS 50 

void initializeStatusLed() {
  if (!USE_RELAY_MODULE) return;

  pinMode(LED_PIN, OUTPUT);
  debugPrint("LED: status controller initialized (Pin 38)");
  
  // A short blue blink indicates processor startup.
  neopixelWrite(LED_PIN, 0, 0, 50); 
  delay(200);
  neopixelWrite(LED_PIN, 0, 0, 0);
}

// Set RGB color while compensating for the onboard GRB LED order.
void setRawColor(uint8_t r, uint8_t g, uint8_t b) {
  // Waveshare ESP32-S3 uses GRB order: green, red, blue.
  neopixelWrite(LED_PIN, g, r, b);
}

void handleStatusLed(bool wifiOk, bool mqttOk) {
  if (!USE_RELAY_MODULE) return;

  unsigned long currentMillis = millis();

  // A critical network error is indicated by a fast red blink.
  if (!wifiOk) {
    static boolean ledState = false;
    // Fast blink with a 100 ms on/off rhythm.
    if (currentMillis % 200 < 100) {
       setRawColor(MAX_BRIGHTNESS, 0, 0);
    } else {
       setRawColor(0, 0, 0);
    }
    return;
  } 

  // A missing MQTT session is indicated by an orange/yellow blink.
  if (!mqttOk) {
    // Orange is represented as red plus a small green component.
    // Interval: 500 ms on, 500 ms off.
    if (currentMillis % 1000 < 500) {
       setRawColor(MAX_BRIGHTNESS, 15, 0);
    } else {
       setRawColor(0, 0, 0);
    }
    return;
  }

  // Healthy operation is indicated by a smooth green breathing effect.
  float val = (exp(sin(currentMillis / 2000.0 * PI)) - 0.36787944) * 108.0;
  
  int brightness = map((int)val, 0, 255, 5, MAX_BRIGHTNESS);
  
  setRawColor(0, brightness, 0); 
}

void setOtaLedState(bool active) {
  if (!USE_RELAY_MODULE) return;

  if (active) {
    // Use cyan/blue during OTA update.
    setRawColor(0, 20, 50); 
  } else {
    setRawColor(0, 0, 0);
  }
}
