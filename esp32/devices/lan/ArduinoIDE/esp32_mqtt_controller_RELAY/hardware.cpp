#include "hardware.h"
#include "config.h"
#include "debug.h"
#include "mqtt_manager.h"
#include "status_led.h"
#include <Wire.h>

// Relay runtime state.
bool deviceStates[20]          = {false};
unsigned long deviceStartTimes[20] = {0};
bool allDevicesOff             = true;

// Effect-controlled relays are protected from the normal auto-off timer.
bool effectControlled[20]      = {false};

byte expanderState = 0x00;

void writeExpander(byte data) {
  Wire.beginTransmission(I2C_EXPANDER_ADDR);
  Wire.write(0x01);
  Wire.write(data);
  byte error = Wire.endTransmission();

  if (error != 0) {
    debugPrint("I2C communication error: " + String(error));
  }
}

void initializeHardware() {
  debugPrint("Initializing " + String(DEVICE_COUNT) + " devices...");

  initializeStatusLed();

  if (USE_RELAY_MODULE) {
    debugPrint("Mode: Waveshare relay module (I2C)");
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

    // The I2C timeout prevents a bus fault from blocking the main loop.
    Wire.setTimeOut(50);

    Wire.beginTransmission(I2C_EXPANDER_ADDR);
    Wire.write(0x03);  // Configuration register.
    Wire.write(0x00);  // All pins as outputs.

    if (Wire.endTransmission() != 0) {
      Serial.println("ERROR: I2C expander not found!");
    } else {
      debugPrint("I2C expander initialized successfully");
    }

    // The initial expander state honors inverted relay channels.
    expanderState = 0x00;
    for (int i = 0; i < DEVICE_COUNT; i++) {
      if (DEVICES[i].inverted) {
        expanderState |= (1 << DEVICES[i].pin);
      }
    }
    writeExpander(expanderState);

  } else {
    debugPrint("Mode: direct GPIO control");
    for (int i = 0; i < DEVICE_COUNT; i++) {
      pinMode(DEVICES[i].pin, OUTPUT);
      digitalWrite(DEVICES[i].pin, DEVICES[i].inverted ? HIGH : LOW);
    }
  }

  // Runtime state starts from a known all-off condition.
  for (int i = 0; i < DEVICE_COUNT; i++) {
    deviceStates[i]     = false;
    deviceStartTimes[i] = 0;
    effectControlled[i] = false;
  }

  allDevicesOff = true;
  debugPrint("Hardware initialized - all devices OFF");
}

void setDevice(int deviceIndex, bool state) {
  if (deviceIndex < 0 || deviceIndex >= DEVICE_COUNT) {
    debugPrint("ERROR: Invalid device index: " + String(deviceIndex));
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
    // Only active relays with a configured timeout are auto-disabled.
    if (!deviceStates[i] || DEVICES[i].autoOffMs == 0) continue;

    // Active effects manage their own relay timing.
    if (effectControlled[i]) continue;

    if (currentTime - deviceStartTimes[i] >= DEVICES[i].autoOffMs) {
      debugPrint("AUTO-OFF: " + String(DEVICES[i].name) + " -> turning off.");
      setDevice(i, false);
      publishDeviceState(i, "auto_off", false);
    }
  }
}

void turnOffAllDevices() {
  debugPrint("Turning all devices off");

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

String getDeviceStatus() {
  String status = "";
  for (int i = 0; i < DEVICE_COUNT; i++) {
    status += String(DEVICES[i].name) + ":" + (deviceStates[i] ? "ON" : "OFF");
    if (i < DEVICE_COUNT - 1) status += ",";
  }
  return status;
}
