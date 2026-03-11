#include "hardware.h"
#include "config.h"
#include "debug.h"
#include "status_led.h"
#include <Wire.h>

// Global device states
bool deviceStates[20]          = {false};
unsigned long deviceStartTimes[20] = {0};
bool allDevicesOff             = true;

// Flags set by effects_manager to protect devices from handleAutoOff()
// while they are under active effect control.
bool effectControlled[20]      = {false};

byte expanderState = 0x00;

// ---------------------------------------------------------------------------
// I2C write helper
// ---------------------------------------------------------------------------
void writeExpander(byte data) {
  Wire.beginTransmission(I2C_EXPANDER_ADDR);
  Wire.write(0x01);
  Wire.write(data);
  byte error = Wire.endTransmission();

  if (error != 0) {
    debugPrint("CHYBA I2C komunikacie: " + String(error));
  }
}

// ---------------------------------------------------------------------------
// initializeHardware
// ---------------------------------------------------------------------------
void initializeHardware() {
  debugPrint("Inicializujem " + String(DEVICE_COUNT) + " zariadeni...");

  initializeStatusLed();

  if (USE_RELAY_MODULE) {
    debugPrint("Rezim: Waveshare Relay Module (I2C)");
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

    // Set I2C timeout – prevents bus hang from blocking the main loop
    Wire.setTimeOut(50);

    Wire.beginTransmission(I2C_EXPANDER_ADDR);
    Wire.write(0x03);  // Configuration register
    Wire.write(0x00);  // All pins as outputs

    if (Wire.endTransmission() != 0) {
      Serial.println("CHYBA: I2C Expander nenajdeny!");
    } else {
      debugPrint("I2C Expander inicializovany OK");
    }

    // Set initial expander state – handle inverted channels
    expanderState = 0x00;
    for (int i = 0; i < DEVICE_COUNT; i++) {
      if (DEVICES[i].inverted) {
        expanderState |= (1 << DEVICES[i].pin);
      }
    }
    writeExpander(expanderState);

  } else {
    debugPrint("Rezim: Direct GPIO Control");
    for (int i = 0; i < DEVICE_COUNT; i++) {
      pinMode(DEVICES[i].pin, OUTPUT);
      digitalWrite(DEVICES[i].pin, DEVICES[i].inverted ? HIGH : LOW);
    }
  }

  // Reset all runtime state
  for (int i = 0; i < DEVICE_COUNT; i++) {
    deviceStates[i]     = false;
    deviceStartTimes[i] = 0;
    effectControlled[i] = false;
  }

  allDevicesOff = true;
  debugPrint("Hardware inicializovane - vsetky zariadenia OFF");
}

// ---------------------------------------------------------------------------
// setDevice
// ---------------------------------------------------------------------------
void setDevice(int deviceIndex, bool state) {
  if (deviceIndex < 0 || deviceIndex >= DEVICE_COUNT) {
    debugPrint("ERROR: Neplatny index zariadenia: " + String(deviceIndex));
    return;
  }

  const Device& device = DEVICES[deviceIndex];
  deviceStates[deviceIndex] = state;

  if (state) {
    deviceStartTimes[deviceIndex] = millis();
    allDevicesOff = false;
  } else {
    bool anyOn = false;
    for (int i = 0; i < DEVICE_COUNT; i++) {
      if (deviceStates[i]) { anyOn = true; break; }
    }
    allDevicesOff = !anyOn;
  }

  if (USE_RELAY_MODULE) {
    bool physicalBit = device.inverted ? !state : state;
    if (physicalBit) expanderState |=  (1 << device.pin);
    else             expanderState &= ~(1 << device.pin);
    writeExpander(expanderState);
  } else {
    bool outputState = device.inverted ? !state : state;
    digitalWrite(device.pin, outputState ? HIGH : LOW);
  }

  debugPrint(String(device.name) + " -> " + (state ? "ON" : "OFF"));
}
void handleAutoOff() {
  unsigned long currentTime = millis();

  for (int i = 0; i < DEVICE_COUNT; i++) {
    // Only process: device is ON + has an autoOff timeout configured
    if (!deviceStates[i] || DEVICES[i].autoOffMs == 0) continue;

    // Skip if effects_manager currently owns this device
    if (effectControlled[i]) continue;

    if (currentTime - deviceStartTimes[i] >= DEVICES[i].autoOffMs) {
      debugPrint("AUTO-OFF: " + String(DEVICES[i].name) + " -> Vypinam.");
      setDevice(i, false);
    }
  }
}

// ---------------------------------------------------------------------------
// turnOffAllDevices
// ---------------------------------------------------------------------------
void turnOffAllDevices() {
  debugPrint("Vypinam vsetky zariadenia");

  if (USE_RELAY_MODULE) {
    expanderState = 0x00;
    for (int i = 0; i < DEVICE_COUNT; i++) {
      if (DEVICES[i].inverted) {
        expanderState |= (1 << DEVICES[i].pin);
      }
    }
    writeExpander(expanderState);
  } else {
    for (int i = 0; i < DEVICE_COUNT; i++) {
      digitalWrite(DEVICES[i].pin, DEVICES[i].inverted ? HIGH : LOW);
    }
  }

  for (int i = 0; i < DEVICE_COUNT; i++) {
    deviceStates[i]     = false;
    effectControlled[i] = false;
  }

  allDevicesOff = true;
}

// ---------------------------------------------------------------------------
// getDeviceStatus
// ---------------------------------------------------------------------------
String getDeviceStatus() {
  String status = "";
  for (int i = 0; i < DEVICE_COUNT; i++) {
    status += String(DEVICES[i].name) + ":" + (deviceStates[i] ? "ON" : "OFF");
    if (i < DEVICE_COUNT - 1) status += ",";
  }
  return status;
}