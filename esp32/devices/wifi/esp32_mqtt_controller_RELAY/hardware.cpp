#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Wire.h>

// Global hardware state
bool deviceStates[20] = {false}; // Max 20 zariadeni
bool allDevicesOff = true;

// Pomocna premenna pre stav expandera (pamatame si, ktore bity su zapnute)
byte expanderState = 0x00;

// Funkcia na zapis do expandera TCA9554
void writeExpander(byte data) {
  Wire.beginTransmission(I2C_EXPANDER_ADDR);
  Wire.write(0x01); // Register 1 = Output Port Register
  Wire.write(data);
  byte error = Wire.endTransmission();
  
  if (error != 0) {
    debugPrint("CHYBA I2C komunikacie: " + String(error));
  }
}

void initializeHardware() {
  debugPrint("Inicializujem " + String(DEVICE_COUNT) + " zariadeni...");

  if (USE_RELAY_MODULE) {
    // --- Inicializacia pre Waveshare Modul (I2C) ---
    debugPrint("Rezim: Waveshare Relay Module (I2C)");
    debugPrint("SDA: " + String(I2C_SDA_PIN) + ", SCL: " + String(I2C_SCL_PIN));
    
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    
    // Nastavenie vsetkych pinov expandera ako OUTPUT
    // Register 3 = Configuration Register (0 = Output, 1 = Input)
    Wire.beginTransmission(I2C_EXPANDER_ADDR);
    Wire.write(0x03); 
    Wire.write(0x00); // Vsetky piny na 0 (OUTPUT)
    
    if (Wire.endTransmission() != 0) {
      Serial.println("CHYBA: I2C Expander nenajdeny! Skontrolujte napajanie.");
    } else {
      debugPrint("I2C Expander inicializovany OK");
    }

    // Vypnutie vsetkych rele na zaciatku
    expanderState = 0x00;
    
    // Ak su rele invertovane (aktivne v 0), musime nastavit 1 pre vypnutie
    for (int i = 0; i < DEVICE_COUNT; i++) {
        if (DEVICES[i].inverted) {
            expanderState |= (1 << DEVICES[i].pin);
        }
    }
    writeExpander(expanderState);

  } else {
    // --- Inicializacia pre Klasicke ESP32 (GPIO) ---
    debugPrint("Rezim: Direct GPIO Control");
    for (int i = 0; i < DEVICE_COUNT; i++) {
      pinMode(DEVICES[i].pin, OUTPUT);
      
      // Nastav zariadenie do OFF stavu
      if (DEVICES[i].inverted) {
        digitalWrite(DEVICES[i].pin, HIGH); // Invertovane rele: HIGH = OFF
      } else {
        digitalWrite(DEVICES[i].pin, LOW);  // Normalne: LOW = OFF
      }
    }
  }

  // Reset stavov v pamati
  for (int i = 0; i < DEVICE_COUNT; i++) {
    deviceStates[i] = false;
    Serial.print(" - ");
    Serial.print(DEVICES[i].name);
    Serial.print(USE_RELAY_MODULE ? " -> Bit " : " -> GPIO ");
    Serial.print(DEVICES[i].pin);
    Serial.println(DEVICES[i].inverted ? " (invertovane)" : "");
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
  allDevicesOff = false;

  if (USE_RELAY_MODULE) {
    // --- Ovladanie cez I2C Expander ---
    // Zistime fyzicky stav (respektujeme inverted)
    bool physicalBit = device.inverted ? !state : state;

    if (physicalBit) {
      expanderState |= (1 << device.pin); // Nastav bit na 1
    } else {
      expanderState &= ~(1 << device.pin); // Nastav bit na 0
    }
    
    writeExpander(expanderState);
    debugPrint(String(device.name) + " (Bit " + String(device.pin) + ") -> " + (state ? "ON" : "OFF"));

  } else {
    // --- Ovladanie cez GPIO ---
    bool outputState = device.inverted ? !state : state;
    digitalWrite(device.pin, outputState ? HIGH : LOW);
    
    debugPrint(String(device.name) + " nastavene na " + (state ? "ON" : "OFF"));
  }
}

void turnOffAllDevices() {
  debugPrint("Vypinam vsetky zariadenia - bezpecnostne vypnutie");
  
  if (USE_RELAY_MODULE) {
    // I2C: Reset stavu
    expanderState = 0x00; 
    
    // Osetrime invertovane rele (pre tie je OFF stav logicka 1)
    for (int i = 0; i < DEVICE_COUNT; i++) {
        if (DEVICES[i].inverted) {
            expanderState |= (1 << DEVICES[i].pin);
        }
    }
    writeExpander(expanderState);

  } else {
    // GPIO: Klasicky cyklus
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
  Serial.println("WARN: Vsetky zariadenia vypnute");
}

String getDeviceStatus() {
  String status = "";
  for (int i = 0; i < DEVICE_COUNT; i++) {
    status += String(DEVICES[i].name) + ":" + (deviceStates[i] ? "ON" : "OFF");
    if (i < DEVICE_COUNT - 1) status += ",";
  }
  return status;
}