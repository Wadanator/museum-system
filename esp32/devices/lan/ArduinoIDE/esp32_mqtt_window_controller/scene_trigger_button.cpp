#include "scene_trigger_button.h"

#include <Arduino.h>
#include <stdio.h>

#include "config.h"
#include "debug.h"
#include "mqtt_manager.h"

namespace {

bool sceneTriggerInitialized = false;
bool lastRawActive = false;
bool stableActive = false;
unsigned long rawChangedAt = 0;
unsigned long lastTriggerAt = 0;

bool readButtonActive() {
  int rawLevel = digitalRead(SCENE_TRIGGER_BUTTON_PIN);
  return SCENE_TRIGGER_BUTTON_ACTIVE_LOW ? rawLevel == LOW : rawLevel == HIGH;
}

void publishSceneStart() {
  if (!isMqttConnected()) {
    debugPrint("Scene trigger DI5 pressed, but MQTT is disconnected");
    return;
  }

  char topic[96];
  snprintf(topic, sizeof(topic), "%s%s", BASE_TOPIC_PREFIX, SCENE_TRIGGER_TOPIC_NAME);

  if (client.publish(topic, SCENE_TRIGGER_PAYLOAD, false)) {
    debugPrint("Scene trigger DI5 sent: " + String(topic) + " -> " + String(SCENE_TRIGGER_PAYLOAD));
  } else {
    debugPrint("Scene trigger DI5 publish failed: " + String(topic));
  }
}

}  // namespace

void initializeSceneTriggerButton() {
  if (!SCENE_TRIGGER_BUTTON_ENABLED) {
    debugPrint("Scene trigger button disabled");
    return;
  }

  pinMode(SCENE_TRIGGER_BUTTON_PIN, SCENE_TRIGGER_BUTTON_INPUT_MODE);
  lastRawActive = readButtonActive();
  stableActive = lastRawActive;
  rawChangedAt = millis();
  lastTriggerAt = 0;
  sceneTriggerInitialized = true;

  debugPrint("Scene trigger button initialized on GPIO" + String(SCENE_TRIGGER_BUTTON_PIN));
}

void handleSceneTriggerButton() {
  if (!SCENE_TRIGGER_BUTTON_ENABLED) return;
  if (!sceneTriggerInitialized) {
    initializeSceneTriggerButton();
  }

  unsigned long currentTime = millis();
  bool rawActive = readButtonActive();

  if (rawActive != lastRawActive) {
    lastRawActive = rawActive;
    rawChangedAt = currentTime;
    return;
  }

  if (currentTime - rawChangedAt < SCENE_TRIGGER_DEBOUNCE_MS) return;
  if (rawActive == stableActive) return;

  stableActive = rawActive;
  if (!stableActive) return;

  if (lastTriggerAt != 0 &&
      currentTime - lastTriggerAt < SCENE_TRIGGER_COOLDOWN_MS) {
    debugPrint("Scene trigger DI5 ignored during cooldown");
    return;
  }

  lastTriggerAt = currentTime;
  publishSceneStart();
}
