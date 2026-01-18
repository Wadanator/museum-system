#include "status_led.h"
#include "config.h"
#include "debug.h"
#include <Adafruit_NeoPixel.h>

// Ukazovateľ na objekt LED (vytvorí sa dynamicky len ak treba)
Adafruit_NeoPixel* rgbLed = nullptr;

void initializeStatusLed() {
  // Ak nie sme na Waveshare doske, LED ignorujeme
  if (!USE_RELAY_MODULE) {
    debugPrint("LED: Standard mode - LED vypnuta");
    return;
  }

  // Inicializácia pre Waveshare (RGB LED na pine 38)
  debugPrint("LED: Waveshare mode - RGB Init (Pin " + String(RGB_LED_PIN) + ")");
  rgbLed = new Adafruit_NeoPixel(1, RGB_LED_PIN, NEO_GRB + NEO_KHZ800);
  rgbLed->begin();
  rgbLed->setBrightness(20); // Nastavenie jasu (0-255)
  rgbLed->setPixelColor(0, rgbLed->Color(0, 0, 255)); // Modrá pri štarte
  rgbLed->show();
}

void handleStatusLed(bool wifiOk, bool mqttOk) {
  // Ak LED nie je inicializovaná, nerob nič
  if (!USE_RELAY_MODULE || rgbLed == nullptr) return;

  static unsigned long lastBlinkTime = 0;
  static bool ledState = false;
  unsigned long interval = 0;
  uint32_t color = 0;

  // Logika stavov a farieb
  if (!wifiOk) {
    // Červená = Chyba WiFi (rýchle blikanie)
    color = rgbLed->Color(255, 0, 0); 
    interval = 200;
  } else if (!mqttOk) {
    // Oranžová = Chyba MQTT (stredné blikanie)
    color = rgbLed->Color(255, 140, 0); 
    interval = 500;
  } else {
    // Zelená = Všetko OK (pomalé dýchanie/blikanie)
    color = rgbLed->Color(0, 255, 0); 
    interval = 2000;
  }

  // Blikanie bez blokovania procesora (bez delay)
  if (millis() - lastBlinkTime >= interval) {
    lastBlinkTime = millis();
    ledState = !ledState;
    
    if (ledState) {
      rgbLed->setPixelColor(0, color);
    } else {
      rgbLed->setPixelColor(0, 0); // Vypnutá
    }
    rgbLed->show();
  }
}

void setOtaLedState(bool active) {
  if (!USE_RELAY_MODULE || rgbLed == nullptr) return;

  if (active) {
    rgbLed->setPixelColor(0, rgbLed->Color(0, 0, 255)); // Modrá = Update beží
  } else {
    rgbLed->setPixelColor(0, 0); // Vypnutá
  }
  rgbLed->show();
}