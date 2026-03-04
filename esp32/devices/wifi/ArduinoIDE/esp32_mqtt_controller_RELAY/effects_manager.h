#ifndef EFFECTS_MANAGER_H
#define EFFECTS_MANAGER_H

#include <Arduino.h>

void initializeEffects();
void handleEffects();
void startEffect(String groupName);
void stopEffect(String groupName);
void stopAllEffects();

#endif