#ifndef EFFECTS_CONFIG_H
#define EFFECTS_CONFIG_H

#include <Arduino.h>

// Maximum number of device indexes assigned to a single effect group.
#define MAX_DEVICES_PER_GROUP 5

struct EffectGroup {
  const char* name;          // Name used in the MQTT effect topic.
  int deviceIndices[MAX_DEVICES_PER_GROUP]; // Device indexes reference DEVICES in config.cpp.
  
  // ON-state timing limits.
  unsigned long minOnMs;     
  unsigned long maxOnMs;
  
  // OFF-state timing limits.
  unsigned long minOffMs;
  unsigned long maxOffMs;
};

// Effect group configuration.
const EffectGroup EFFECT_GROUPS[] = {
  
  // Group for lights 4 and 5.
  // Command topic: room1/effects/group1.
  {
    "group1",               
    {6, 7, -1},             // Indexes for light/4 and light/5.
    75, 500,                // ON: short pulse window for lightning-style flashes.
    150, 1500               // OFF: short random pause between flashes.
  },

  // Group for light 1.
  // Command topic: room1/effects/alone.
  // Intended behavior: short pulse, less frequent.
  {
    "alone",               
    {2, -1},                // Index for light/1.
    60, 100,                // ON: very short pulse; keep relay wear in mind.
    2000, 5000              // OFF: sparse pause from 2 to 5 seconds.
  }
};

const int EFFECT_GROUP_COUNT = sizeof(EFFECT_GROUPS) / sizeof(EffectGroup);

#endif
