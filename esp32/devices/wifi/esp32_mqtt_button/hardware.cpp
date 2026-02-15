#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Arduino.h>

// Stavové premenné pre debouncing
int lastButtonState = HIGH;  
int currentButtonState = HIGH;
unsigned long lastDebounceTime = 0;

// Ochrana pred spamovaním (Cooldown)
unsigned long lastValidPressTime = 0; 

void initializeHardware() {
  debugPrint("Initializing Hardware (External Pull-up)...");
  
  // DÔLEŽITÉ: Používame INPUT, pretože máte externý rezistor na 3.3V
  pinMode(BUTTON_PIN, INPUT);
  
  debugPrint("Button initialized on PIN " + String(BUTTON_PIN));
}

bool wasButtonPressed() {
  int reading = digitalRead(BUTTON_PIN);
  unsigned long currentTime = millis();

  // Detekcia fyzickej zmeny stavu
  if (reading != lastButtonState) {
    lastDebounceTime = currentTime;
  }

  bool verifiedPress = false;

  // 1. Debounce filter (50ms) - odstránenie mechanického šumu
  if ((currentTime - lastDebounceTime) > DEBOUNCE_DELAY) {
    
    // Ak je stav stabilný a zmenil sa oproti predchádzajúcemu
    if (reading != currentButtonState) {
      currentButtonState = reading;

      // Logika: LOW znamená stlačené (spojené s GND)
      if (currentButtonState == LOW) {
        
        // 2. Cooldown filter (ochrana pred "pinzetou" a rýchlym spamom)
        if (currentTime - lastValidPressTime >= BUTTON_COOLDOWN) {
          debugPrint("Button logic: PRESSED (Valid)");
          lastValidPressTime = currentTime; 
          verifiedPress = true;
        } else {
          // Len pre debug, aby ste videli, že kód žije, ale blokuje spam
          debugPrint("Button: Blocked by cooldown");
        }
      }
    }
  }

  lastButtonState = reading;
  return verifiedPress;
}

void turnOffHardware() {
  debugPrint("Hardware safe mode active");
}