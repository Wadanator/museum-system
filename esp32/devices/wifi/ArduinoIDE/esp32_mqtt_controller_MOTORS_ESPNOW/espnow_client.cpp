#include "espnow_client.h"
#include "config.h"
#include "hardware.h"
#include "motor_commands.h"
#include <esp_random.h>

namespace {
museum::Radio radio;
museum::PeerSender sender(radio, 0);
class Actions : public museum::MotorActions {
 public:
  bool execute(museum::Target target, const char* command) override {
    return executeMotorCommand(target, command);
  }
  void hardStop() override { turnOffHardware(); }
  museum::Snapshot snapshot() override { return readMotorSnapshot(); }
  uint32_t nonce() override { return esp_random(); }
} actions;
museum::MotorLink motorLink(sender, actions, ESPNOW_SELF_NODE, ESPNOW_MASTER_NODE, ESPNOW_TIMING);
bool started = false;
bool wasLinked = false;
}

bool initializeEspNowClient() {
  if (!ESPNOW_ENABLED) return false;
  started = ESPNOW_TIMING.valid() &&
      radio.begin(ESPNOW_CHANNEL, ESPNOW_SELF_NODE, ESPNOW_MASTER_PEER, 1, ESPNOW_PMK);
  Serial.println(started ? "ESP-NOW motor: waiting for configured master" :
      "ESP-NOW CONFIG/INIT ERROR: check master STA MAC, node IDs, channel and keys; motors locked OFF");
  return started;
}

void espNowClientLoop() {
  if (!started) { if (!hardwareOff) turnOffHardware(); return; }
  if (!radio.healthy()) {
    motorLink.suspend(); started = false;
    Serial.println("ESP-NOW radio fault: motors OFF; restart required");
    return;
  }
  motorLink.tick(millis());
  museum::RadioEvent event;
  while (radio.poll(event)) motorLink.receive(event.frame, millis());
  if (motorLink.linked() != wasLinked) {
    wasLinked = motorLink.linked();
    Serial.println(wasLinked ? "ESP-NOW master connected" : "ESP-NOW master lost/disabled: motors OFF");
  }
}
