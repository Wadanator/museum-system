#include "effects_manager.h"
#include "effects_config.h"
#include "config.h"
#include "hardware.h"
#include "debug.h"

// Stav efektov
bool groupActive[EFFECT_GROUP_COUNT];

// Stav pre každé fyzické zariadenie (aby blikali nezávisle)
struct DeviceRuntimeState {
  unsigned long nextSwitchTime;
  bool isEffectOn;
  int activeGroupIndex; // -1 ak žiadna
};

// Pole pre stavy (veľkosť podľa hardware.cpp)
DeviceRuntimeState deviceRuntimes[20]; 

void initializeEffects() {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    groupActive[i] = false;
  }
  for (int i = 0; i < 20; i++) {
    deviceRuntimes[i].activeGroupIndex = -1;
    deviceRuntimes[i].isEffectOn = false;
  }
  debugPrint("Effects: Manager Ready");
}

void startEffect(String groupName) {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (String(EFFECT_GROUPS[i].name) == groupName) {
      if (!groupActive[i]) {
        groupActive[i] = true;
        debugPrint("Efekt START: " + groupName);
        
        // Aktivácia zariadení v skupine
        for (int j = 0; j < MAX_DEVICES_PER_GROUP; j++) {
          int devIdx = EFFECT_GROUPS[i].deviceIndices[j];
          if (devIdx == -1) break;
          
          deviceRuntimes[devIdx].activeGroupIndex = i;
          deviceRuntimes[devIdx].isEffectOn = false;
          // Náhodný štart, nech nezačnú všetky naraz
          deviceRuntimes[devIdx].nextSwitchTime = millis() + random(10, 500); 
        }
      }
      return;
    }
  }
  debugPrint("Neznámy efekt: " + groupName);
}

void stopEffect(String groupName) {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (String(EFFECT_GROUPS[i].name) == groupName) {
      groupActive[i] = false;
      debugPrint("Efekt STOP: " + groupName);
      
      // Vypnutie zariadení
      for (int j = 0; j < MAX_DEVICES_PER_GROUP; j++) {
        int devIdx = EFFECT_GROUPS[i].deviceIndices[j];
        if (devIdx == -1) break;
        
        if (deviceRuntimes[devIdx].activeGroupIndex == i) {
          deviceRuntimes[devIdx].activeGroupIndex = -1;
          setDevice(devIdx, false); 
        }
      }
      return;
    }
  }
}

void stopAllEffects() {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (groupActive[i]) {
      stopEffect(EFFECT_GROUPS[i].name);
    }
  }
}

void handleEffects() {
  unsigned long currentTime = millis();

  for (int i = 0; i < DEVICE_COUNT; i++) {
    int groupIdx = deviceRuntimes[i].activeGroupIndex;
    
    // Ak zariadenie neriadi efekt, preskoč
    if (groupIdx == -1 || !groupActive[groupIdx]) continue;

    if (currentTime >= deviceRuntimes[i].nextSwitchTime) {
      const EffectGroup& group = EFFECT_GROUPS[groupIdx];
      
      // Prepni stav
      deviceRuntimes[i].isEffectOn = !deviceRuntimes[i].isEffectOn;
      setDevice(i, deviceRuntimes[i].isEffectOn);

      // Naplánuj ďalšiu zmenu
      long nextInterval;
      if (deviceRuntimes[i].isEffectOn) {
        // Sme ON -> čakáme random čas ON
        nextInterval = random(group.minOnMs, group.maxOnMs);
      } else {
        // Sme OFF -> čakáme random čas OFF (pauza)
        nextInterval = random(group.minOffMs, group.maxOffMs);
      }

      deviceRuntimes[i].nextSwitchTime = currentTime + nextInterval;
    }
  }
}