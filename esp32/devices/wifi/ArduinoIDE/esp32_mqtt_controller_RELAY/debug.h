#ifndef DEBUG_H
#define DEBUG_H

#include <Arduino.h>

// String overload – for existing callers that build a String message
void debugPrint(const String& message);

// const char* overload – zero heap allocation, use this in hot paths
void debugPrint(const char* message);

#endif