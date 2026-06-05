#ifndef DEBUG_H
#define DEBUG_H

#include <Arduino.h>

// Diagnostic output for dynamically composed messages.
void debugPrint(const String& message);

// Diagnostic output for static messages.
void debugPrint(const char* message);

#endif
