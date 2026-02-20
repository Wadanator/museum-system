#ifndef EFFECTS_CONFIG_H
#define EFFECTS_CONFIG_H

#include <Arduino.h>

// Maximálny počet zariadení v jednej skupine
#define MAX_DEVICES_PER_GROUP 5

struct EffectGroup {
  const char* name;          // Názov pre MQTT
  int deviceIndices[MAX_DEVICES_PER_GROUP]; // Indexy z config.cpp
  
  // Časy pre stav ZAPNUTÉ (ON)
  unsigned long minOnMs;     
  unsigned long maxOnMs;
  
  // Časy pre stav VYPNUTÉ (OFF - pauza)
  unsigned long minOffMs;
  unsigned long maxOffMs;
};

// =============================================================================
// KONFIGURÁCIA TVOJICH SKUPÍN
// =============================================================================
const EffectGroup EFFECT_GROUPS[] = {
  
  // 1. Skupina: Svetlá 4 a 5 (Indexy 6, 7)
  // Príkaz: room1/effects/group1 -> ON
  {
    "group1",               
    {6, 7, -1},             // Indexy pre light/4 a light/5
    75, 500,                // ON: 50ms až 0.25s (Blesky)
    150, 1500               // OFF: Rýchlejšie opakovanie
  },

  // 2. Skupina: ALONE - Svetlo 1 (Index 2)
  // Príkaz: room1/effects/alone -> ON
  // Zadanie: "krátko, ale menej často"
  {
    "alone",               
    {2, -1},                // Index pre light/1
    60, 100,                // ON: Veľmi krátke (cca 0.05s) - POZOR, toto je limit relé!
    2000, 5000              // OFF: Zriedkavé (pauza 2 až 5 sekúnd)
  }
};

const int EFFECT_GROUP_COUNT = sizeof(EFFECT_GROUPS) / sizeof(EffectGroup);

#endif