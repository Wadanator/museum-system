#include "status_led.h"
#include "config.h"
#include "debug.h"

// Maximum brightness (0-255). 50 is suitable for indoor diagnostics.
#define MAX_BRIGHTNESS 50

void initializeStatusLed() {
  pinMode(RGB_LED_PIN, OUTPUT);
  debugPrint("LED: status controller initialized (Pin " + String(RGB_LED_PIN) + ")");

  // A short blue blink indicates processor startup.
  neopixelWrite(RGB_LED_PIN, 0, 0, 50);
  delay(200);
  neopixelWrite(RGB_LED_PIN, 0, 0, 0);
}

// Set RGB color while compensating for the onboard GRB LED order.
void setRawColor(uint8_t r, uint8_t g, uint8_t b) {
  // Waveshare ESP32-S3 uses GRB order: green, red, blue.
  neopixelWrite(RGB_LED_PIN, g, r, b);
}

void handleStatusLed(bool wifiOk, bool mqttOk) {
  unsigned long currentMillis = millis();

  if (!wifiOk) {
    if (currentMillis % 200 < 100) {
       setRawColor(MAX_BRIGHTNESS, 0, 0);
    } else {
       setRawColor(0, 0, 0);
    }
    return;
  }

  if (!mqttOk) {
    if (currentMillis % 1000 < 500) {
       setRawColor(MAX_BRIGHTNESS, 15, 0);
    } else {
       setRawColor(0, 0, 0);
    }
    return;
  }

  // Healthy operation is indicated by a smooth green breathing animation.
  float val = (exp(sin(currentMillis / 2000.0 * PI)) - 0.36787944) * 108.0;
  int brightness = map((int)val, 0, 255, 5, MAX_BRIGHTNESS);
  setRawColor(0, brightness, 0);
}

void setOtaLedState(bool active) {
  if (active) {
    setRawColor(0, 20, 50);
  } else {
    setRawColor(0, 0, 0);
  }
}
