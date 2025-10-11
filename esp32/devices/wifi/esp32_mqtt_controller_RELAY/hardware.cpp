#include "hardware.h"
#include "config.h"
#include "debug.h"

// Global hardware state
bool deviceStates[20] = {false}; // Max 20 zariadení
bool allDevicesOff = true;

void initializeHardware() {
  debugPrint("Inicializujem " + String(DEVICE_COUNT) + " zariadení...");

  for (int i = 0; i < DEVICE_COUNT; i++) {
    pinMode(DEVICES[i].pin, OUTPUT);
    
    // Nastav zariadenie do OFF stavu
    if (DEVICES[i].inverted) {
      digitalWrite(DEVICES[i].pin, HIGH); // Invertované relé: HIGH = OFF
    } else {
      digitalWrite(DEVICES[i].pin, LOW);  // Normálne: LOW = OFF
    }
    
    deviceStates[i] = false;
    
    Serial.print("  ✅ ");
    Serial.print(DEVICES[i].name);
    Serial.print(" -> GPIO ");
    Serial.print(DEVICES[i].pin);
    Serial.println(DEVICES[i].inverted ? " (invertované)" : "");
  }

  allDevicesOff = true;
  debugPrint("Hardware inicializované - všetky zariadenia OFF");
}

void setDevice(int deviceIndex, bool state) {
  if (deviceIndex < 0 || deviceIndex >= DEVICE_COUNT) {
    debugPrint("ERROR: Neplatný index zariadenia: " + String(deviceIndex));
    return;
  }

  const Device& device = DEVICES[deviceIndex];
  deviceStates[deviceIndex] = state;

  // Aplikuj stav s ohľadom na invertované relé
  bool outputState = device.inverted ? !state : state;
  digitalWrite(device.pin, outputState ? HIGH : LOW);

  debugPrint(String(device.name) + " nastavené na " + (state ? "ON" : "OFF") + 
             " (pin " + String(device.pin) + " = " + (outputState ? "HIGH" : "LOW") + ")");
  
  allDevicesOff = false;
}

void turnOffAllDevices() {
  debugPrint("Vypínam všetky zariadenia - bezpečnostné vypnutie");
  
  for (int i = 0; i < DEVICE_COUNT; i++) {
    if (DEVICES[i].inverted) {
      digitalWrite(DEVICES[i].pin, HIGH); // Invertované: HIGH = OFF
    } else {
      digitalWrite(DEVICES[i].pin, LOW);  // Normálne: LOW = OFF
    }
    deviceStates[i] = false;
  }

  allDevicesOff = true;
  Serial.println("⚠️  Všetky zariadenia vypnuté (strata MQTT spojenia)");
}

String getDeviceStatus() {
  String status = "";
  for (int i = 0; i < DEVICE_COUNT; i++) {
    status += String(DEVICES[i].name) + ":" + (deviceStates[i] ? "ON" : "OFF");
    if (i < DEVICE_COUNT - 1) status += ",";
  }
  return status;
}