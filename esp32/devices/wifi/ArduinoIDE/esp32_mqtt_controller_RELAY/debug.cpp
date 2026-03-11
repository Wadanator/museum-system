#include "debug.h"
#include "config.h"

// String overload – existing callers unchanged
void debugPrint(const String& message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}

// const char* overload – zero heap allocation
// Use this in callback hot paths to avoid String construction.
void debugPrint(const char* message) {
  if (DEBUG) {
    Serial.print("[DEBUG] ");
    Serial.print(millis());
    Serial.print("ms - ");
    Serial.println(message);
  }
}