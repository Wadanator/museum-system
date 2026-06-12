#include "effects_manager.h"
#include "effects_config.h"
#include "config.h"
#include "hardware.h"
#include "debug.h"

// Active state is tracked independently for each effect group.
bool groupActive[EFFECT_GROUP_COUNT];

// Each relay keeps its own effect timing to avoid synchronized switching.
struct DeviceRuntimeState {
  unsigned long nextSwitchTime;
  bool isEffectOn;
  int activeGroupIndex;   // -1 means the relay is not under effect control.
};

DeviceRuntimeState deviceRuntimes[20];

void initializeEffects() {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    groupActive[i] = false;
  }
  for (int i = 0; i < 20; i++) {
    deviceRuntimes[i].activeGroupIndex = -1;
    deviceRuntimes[i].isEffectOn       = false;
    deviceRuntimes[i].nextSwitchTime   = 0;
  }
  debugPrint("Effects: Manager Ready");
}

void startEffect(String groupName) {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (String(EFFECT_GROUPS[i].name) != groupName) continue;

    if (!groupActive[i]) {
      groupActive[i] = true;
      debugPrint("Effect START: " + groupName);

      for (int j = 0; j < MAX_DEVICES_PER_GROUP; j++) {
        int devIdx = EFFECT_GROUPS[i].deviceIndices[j];
        if (devIdx == -1) break;

        deviceRuntimes[devIdx].activeGroupIndex = i;
        deviceRuntimes[devIdx].isEffectOn       = false;

        effectControlled[devIdx] = true;

        // Staggered start times prevent simultaneous relay switching.
        deviceRuntimes[devIdx].nextSwitchTime = millis() + random(10, 500);
      }
    }
    return;
  }
  debugPrint("Unknown effect: " + groupName);
}

void stopEffect(String groupName) {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (String(EFFECT_GROUPS[i].name) != groupName) continue;

    groupActive[i] = false;
    debugPrint("Effect STOP: " + groupName);

    for (int j = 0; j < MAX_DEVICES_PER_GROUP; j++) {
      int devIdx = EFFECT_GROUPS[i].deviceIndices[j];
      if (devIdx == -1) break;

      if (deviceRuntimes[devIdx].activeGroupIndex == i) {
        deviceRuntimes[devIdx].activeGroupIndex = -1;
        deviceRuntimes[devIdx].isEffectOn       = false;
        effectControlled[devIdx] = false;

        setDevice(devIdx, false);
      }
    }
    return;
  }
}

void stopAllEffects() {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (groupActive[i]) {
      stopEffect(EFFECT_GROUPS[i].name);
    }
  }
}

bool isEffectActive(String groupName) {
  for (int i = 0; i < EFFECT_GROUP_COUNT; i++) {
    if (String(EFFECT_GROUPS[i].name) == groupName) {
      return groupActive[i];
    }
  }
  return false;
}

void handleEffects() {
  unsigned long currentTime = millis();

  for (int i = 0; i < DEVICE_COUNT; i++) {
    int groupIdx = deviceRuntimes[i].activeGroupIndex;

    // Relays outside an active effect group are left to normal control.
    if (groupIdx == -1 || !groupActive[groupIdx]) continue;

    if (currentTime >= deviceRuntimes[i].nextSwitchTime) {
      const EffectGroup& group = EFFECT_GROUPS[groupIdx];

      deviceRuntimes[i].isEffectOn = !deviceRuntimes[i].isEffectOn;
      setDevice(i, deviceRuntimes[i].isEffectOn);

      long nextInterval = deviceRuntimes[i].isEffectOn
        ? random(group.minOnMs,  group.maxOnMs)
        : random(group.minOffMs, group.maxOffMs);

      deviceRuntimes[i].nextSwitchTime = currentTime + nextInterval;
    }
  }
}
