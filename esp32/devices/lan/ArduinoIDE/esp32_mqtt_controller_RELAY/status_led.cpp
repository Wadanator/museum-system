#include "status_led.h"
#include "config.h"
#include "debug.h"

// Natvrdo definovaný PIN pre Waveshare dosku
#define LED_PIN 38

// Maximálny jas (0-255). 
// 50 je dostatočné pre interiér, 255 je veľmi silné (môže oslepovať).
#define MAX_BRIGHTNESS 50 

void initializeStatusLed() {
  if (!USE_RELAY_MODULE) return;

  pinMode(LED_PIN, OUTPUT);
  debugPrint("LED: Advanced Status Mode Init (Pin 38)");
  
  // Test pri štarte: Krátke bliknutie na modro (Signál, že CPU žije)
  // GRB poradie: (0, 0, 50) -> Modrá
  neopixelWrite(LED_PIN, 0, 0, 50); 
  delay(200);
  neopixelWrite(LED_PIN, 0, 0, 0);
}

// Pomocná funkcia na nastavenie farby s opravou GRB
// Vstup: Červená, Zelená, Modrá (0-255)
void setRawColor(uint8_t r, uint8_t g, uint8_t b) {
  // Waveshare ESP32-S3 má poradie GRB (Green, Red, Blue)
  // Prvý argument je fyzicky Zelená, druhý Červená, tretí Modrá
  neopixelWrite(LED_PIN, g, r, b);
}

void handleStatusLed(bool wifiOk, bool mqttOk) {
  if (!USE_RELAY_MODULE) return;

  unsigned long currentMillis = millis();

  // ---------------------------------------------------------
  // STAV 1: CRITICAL ERROR - Žiadna WiFi
  // Efekt: Rýchly agresívny stroboskop (Červená)
  // ---------------------------------------------------------
  if (!wifiOk) {
    static boolean ledState = false;
    // Veľmi rýchle blikanie (100ms interval)
    if (currentMillis % 200 < 100) {
       setRawColor(MAX_BRIGHTNESS, 0, 0); // Červená
    } else {
       setRawColor(0, 0, 0); // Tma
    }
    return;
  } 

  // ---------------------------------------------------------
  // STAV 2: SERVER ERROR - WiFi OK, ale žiadne MQTT
  // Efekt: Pravidelné blikanie (Oranžová/Žltá)
  // ---------------------------------------------------------
  if (!mqttOk) {
    // Oranžová sa mieša ako Veľa Červenej + Trochu Zelenej
    // Interval 500ms zapnuté, 500ms vypnuté
    if (currentMillis % 1000 < 500) {
       setRawColor(MAX_BRIGHTNESS, 15, 0); // Oranžová (R=Max, G=slabšia)
    } else {
       setRawColor(0, 0, 0); // Tma
    }
    return;
  }

  // ---------------------------------------------------------
  // STAV 3: ALL SYSTEMS GO - Všetko funguje
  // Efekt: "Dýchanie" (Breathing) - Plynulá Zelená
  // ---------------------------------------------------------
  
  // Matematika pre dýchanie: Použijeme funkciu sínus
  // Perióda dýchania cca 3 sekundy
  float val = (exp(sin(currentMillis / 2000.0 * PI)) - 0.36787944) * 108.0;
  
  // Mapovanie na náš maximálny jas
  int brightness = map((int)val, 0, 255, 5, MAX_BRIGHTNESS);
  
  // Nastavenie Zelenej farby s vypočítaným jasom
  setRawColor(0, brightness, 0); 
}

void setOtaLedState(bool active) {
  if (!USE_RELAY_MODULE) return;

  if (active) {
    // Počas update svieti tyrkysová/modrá
    setRawColor(0, 20, 50); 
  } else {
    setRawColor(0, 0, 0);
  }
}