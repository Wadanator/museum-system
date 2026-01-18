#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Wire.h>

// Global hardware state
bool deviceStates[20] = {false}; 
unsigned long deviceStartTimes[20] = {0};
bool allDevicesOff = true;

byte expanderState = 0x00;

void writeExpander(byte data) {
  Wire.beginTransmission(I2C_EXPANDER_ADDR);
  Wire.write(0x01); 
  Wire.write(data);
  byte error = Wire.endTransmission();
  
  if (error != 0) {
    debugPrint("CHYBA I2C komunikacie: " + String(error));
  }
}

void initializeHardware() {
  debugPrint("Inicializujem " + String(DEVICE_COUNT) + " zariadeni...");

  if (USE_RELAY_MODULE) {
    debugPrint("Rezim: Waveshare Relay Module (I2C)");
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    
    Wire.beginTransmission(I2C_EXPANDER_ADDR);
    Wire.write(0x03); 
    Wire.write(0x00); 
    
    if (Wire.endTransmission() != 0) {
      Serial.println("CHYBA: I2C Expander nenajdeny!");
    } else {
      debugPrint("I2C Expander inicializovany OK");
    }

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
      if (DEVICES[i].inverted) {
        digitalWrite(DEVICES[i].pin, HIGH);
      } else {
        digitalWrite(DEVICES[i].pin, LOW);
      }
    }
  }

  // Reset stavov
  for (int i = 0; i < DEVICE_COUNT; i++) {
    deviceStates[i] = false;
    deviceStartTimes[i] = 0;
  }

  allDevicesOff = true;
  debugPrint("Hardware inicializovane - vsetky zariadenia OFF");
}

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
    for(int i=0; i<DEVICE_COUNT; i++) { if(deviceStates[i]) anyOn = true; }
    allDevicesOff = !anyOn;
  }

  if (USE_RELAY_MODULE) {
    bool physicalBit = device.inverted ? !state : state;
    if (physicalBit) {
      expanderState |= (1 << device.pin);
    } else {
      expanderState &= ~(1 << device.pin);
    }
    writeExpander(expanderState);
    debugPrint(String(device.name) + " -> " + (state ? "ON" : "OFF"));

  } else {
    bool outputState = device.inverted ? !state : state;
    digitalWrite(device.pin, outputState ? HIGH : LOW);
    debugPrint(String(device.name) + " -> " + (state ? "ON" : "OFF"));
  }
}

void handleAutoOff() {
  unsigned long currentTime = millis();
  
  for (int i = 0; i < DEVICE_COUNT; i++) {
    // Kontrolujeme len ak je zariadenie zapnute (ON) a ma nastaveny limit (>0)
    if (deviceStates[i] && DEVICES[i].autoOffMs > 0) {
      
      // Pozor na pretecenia millis(), pouzivame odcitanie
      if (currentTime - deviceStartTimes[i] >= DEVICES[i].autoOffMs) {
        debugPrint("⏱️ AUTO-OFF: " + String(DEVICES[i].name) + " bezal " + String(DEVICES[i].autoOffMs) + "ms -> Vypinam.");
        setDevice(i, false); // Vypneme ho
      }
    }
  }
}

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
      if (DEVICES[i].inverted) {
        digitalWrite(DEVICES[i].pin, HIGH);
      } else {
        digitalWrite(DEVICES[i].pin, LOW);
      }
    }
  }

  for (int i = 0; i < DEVICE_COUNT; i++) {
    deviceStates[i] = false;
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