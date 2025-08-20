#include "debug.h"
#include "config.h"

void debugPrint(const String& message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}