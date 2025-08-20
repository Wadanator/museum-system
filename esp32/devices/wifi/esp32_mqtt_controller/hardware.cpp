#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Arduino.h>

// Global hardware state
bool hardwareOff = false;

void initializeHardware() {
  pinMode(MOTOR_PIN, OUTPUT);
  pinMode(LIGHT_PIN, OUTPUT);
  pinMode(STEAM_PIN, OUTPUT);
  turnOffHardware();
  debugPrint("Hardware initialized");
}

void controlMotor(const char* command) {
  if (strcmp(command, "START") == 0) {
    digitalWrite(MOTOR_PIN, HIGH);
    debugPrint("Motor Started");
    hardwareOff = false;
  } else if (strcmp(command, "STOP") == 0) {
    digitalWrite(MOTOR_PIN, LOW);
    debugPrint("Motor Stopped");
  } else {
    debugPrint("Unknown motor command: " + String(command));
  }
}

void controlLight(const char* command) {
  if (strcmp(command, "ON") == 0) {
    digitalWrite(LIGHT_PIN, HIGH);
    debugPrint("Light ON");
    hardwareOff = false;
  } else if (strcmp(command, "OFF") == 0) {
    digitalWrite(LIGHT_PIN, LOW);
    debugPrint("Light OFF");
  } else {
    debugPrint("Unknown light command: " + String(command));
  }
}

void controlSteam(const char* command) {
  if (strcmp(command, "ON") == 0) {
    digitalWrite(STEAM_PIN, HIGH);
    debugPrint("Steam ON");
    hardwareOff = false;
  } else if (strcmp(command, "OFF") == 0) {
    digitalWrite(STEAM_PIN, LOW);
    debugPrint("Steam OFF");
  } else {
    debugPrint("Unknown steam command: " + String(command));
  }
}

void turnOffHardware() {
  digitalWrite(MOTOR_PIN, LOW);
  digitalWrite(LIGHT_PIN, LOW);
  digitalWrite(STEAM_PIN, LOW);
  debugPrint("All hardware turned OFF due to disconnection");
  hardwareOff = true;
}