#include "espnow_bridge.h"
#include "config.h"
#include "mqtt_manager.h"
#include "wifi_manager.h"
#include <esp_random.h>
#include <new>

namespace {
museum::Radio radio;
bool initialized = false, suspended = false, mqttWasConnected = false;
bool radioReady = false;
bool stopWaiting = false, stopOk = true;
uint8_t stopRemaining = 0;
constexpr uint32_t StopCookie = 3;

void feedback(const char* topic, bool ok) {
  if (!isMqttConnected()) return;
  char name[128];
  snprintf(name, sizeof(name), "%s/feedback", topic);
  client.publish(name, ok ? "OK" : "ERROR", false);
}

void stopFeedback(bool ok) {
  char topic[96];
  snprintf(topic, sizeof(topic), "%sSTOP", BASE_TOPIC_PREFIX);
  feedback(topic, ok);
}

class Peer : public museum::Sender, public museum::MasterEvents {
 public:
  size_t index;
  museum::MasterLink link;
  museum::Snapshot state;
  bool stateValid = false, dirty[2] = {false, false};
  bool statusValid = false, statusOnline = false;
  uint32_t lastStatus = 0, lastPublishAttempt = 0;
  Peer(size_t i, uint32_t session)
      : index(i), link(*this, *this, ESPNOW_SELF_NODE, ESPNOW_PEERS[i].node, session, ESPNOW_TIMING) {}
  bool send(const museum::Frame& frame) override { return radioReady && radio.send(index, frame); }
  void completed(uint32_t cookie, bool ok) override {
    if (cookie == StopCookie) {
      if (stopWaiting) {
        stopOk = stopOk && ok;
        if (stopRemaining && --stopRemaining == 0) {
          stopWaiting = false; stopFeedback(stopOk);
        }
      }
    } else if (cookie >= 1 && cookie <= 2) {
      feedback(ESPNOW_ROUTES[index].topics[cookie - 1], ok);
    }
  }
  void snapshot(const museum::Snapshot& value) override {
    for (size_t i = 0; i < 2; ++i) {
      const auto& a = value.motors[i]; const auto& b = state.motors[i];
      dirty[i] = dirty[i] || !stateValid || a.on != b.on || a.speed != b.speed || a.direction != b.direction;
    }
    state = value; stateValid = true;
  }
  void publish(uint32_t now, bool force) {
    if (!force && museum::elapsed(now, lastPublishAttempt) < 250) return;
    lastPublishAttempt = now;
    const bool online = radioReady && link.online(now);
    char topic[128];
    if (force || !statusValid || online != statusOnline ||
        museum::elapsed(now, lastStatus) >= ESPNOW_PROXY_STATUS_INTERVAL_MS) {
      snprintf(topic, sizeof(topic), "devices/%s/status", ESPNOW_ROUTES[index].nodeId);
      if (client.publish(topic, online ? "online" : "offline", true)) {
        if (!statusValid || online != statusOnline)
          Serial.printf("ESP-NOW peer %s: %s\n", ESPNOW_ROUTES[index].nodeId, online ? "online" : "offline");
        statusValid = true; statusOnline = online; lastStatus = now;
      }
    }
    // Never invent OFF on loss of contact. The backend uses node availability.
    if (!stateValid || !online) return;
    for (size_t i = 0; i < 2; ++i) {
      if (!dirty[i] && !force) continue;
      const auto& m = state.motors[i];
      char payload[256];
      snprintf(topic, sizeof(topic), "%s/state", ESPNOW_ROUTES[index].topics[i]);
      const int length = snprintf(payload, sizeof(payload),
          "{\"state\":\"%s\",\"direction\":\"%s\",\"speed\":%u,\"node_id\":\"%s\",\"source\":\"espnow_proxy\",\"ts_ms\":%lu}",
          m.on ? "ON" : "OFF", m.direction == 'L' ? "LEFT" : m.direction == 'R' ? "RIGHT" : "STOP",
          unsigned(m.speed), ESPNOW_ROUTES[index].nodeId, static_cast<unsigned long>(now));
      if (length > 0 && size_t(length) < sizeof(payload) && client.publish(topic, payload, true)) dirty[i] = false;
    }
  }
};

alignas(Peer) uint8_t storage[museum::MaxPeers][sizeof(Peer)];
Peer* peers[museum::MaxPeers] = {};
size_t peerCount = 0;

bool validRoutes() {
  if (!ESPNOW_PEER_COUNT || ESPNOW_PEER_COUNT > museum::MaxPeers ||
      !ESPNOW_TIMING.valid() || ESPNOW_PROXY_STATUS_INTERVAL_MS < 1000 ||
      ESPNOW_PROXY_STATUS_INTERVAL_MS > 10000) return false;
  for (size_t i = 0; i < ESPNOW_PEER_COUNT; ++i) {
    const auto& route = ESPNOW_ROUTES[i];
    if (!route.nodeId || !*route.nodeId || strlen(route.nodeId) > 48 || !strcmp(route.nodeId, CLIENT_ID)) return false;
    for (const char* p = route.nodeId; *p; ++p)
      if (!isalnum(static_cast<unsigned char>(*p)) && *p != '_' && *p != '-') return false;
    for (size_t m = 0; m < 2; ++m) {
      const char* t = route.topics[m];
      if (!t || !*t || strlen(t) > 80 || strpbrk(t, "+#") || strstr(t, "/state") ||
          strstr(t, "/feedback") || strstr(t, "/status") || strstr(t, "/STOP") || strstr(t, "/effects/")) return false;
      for (int d = 0; d < DEVICE_COUNT; ++d) {
        char local[128];
        snprintf(local, sizeof(local), "%s%s", BASE_TOPIC_PREFIX, DEVICES[d].name);
        if (!strcmp(t, local)) return false;
      }
      for (size_t j = 0; j <= i; ++j) {
        if (j < i && !strcmp(route.nodeId, ESPNOW_ROUTES[j].nodeId)) return false;
        for (size_t n = 0; n < 2; ++n)
          if ((j < i || n < m) && !strcmp(t, ESPNOW_ROUTES[j].topics[n])) return false;
      }
    }
  }
  return true;
}
}

void initializeEspNowBridge() {
  if (!RELAY_MOTOR_BRIDGE_ENABLED) { Serial.println("Profile: legacy relay MQTT"); return; }
  Serial.println(RELAY_WIFI_FALLBACK_ENABLED
      ? "Profile: LAN MQTT + same-channel WiFi fallback + ESP-NOW motor bridge"
      : "Profile: LAN MQTT + ESP-NOW motor bridge (WiFi fallback disabled)");
  if (!validRoutes()) { Serial.println("ESP-NOW route/timing configuration invalid"); return; }
  peerCount = ESPNOW_PEER_COUNT;
  const uint32_t session = esp_random();
  for (size_t i = 0; i < peerCount; ++i) peers[i] = new (storage[i]) Peer(i, session);
  initialized = radio.begin(ESPNOW_CHANNEL, ESPNOW_SELF_NODE, ESPNOW_PEERS, peerCount, ESPNOW_PMK);
  if (!initialized)
    Serial.println("ESP-NOW CONFIG/INIT ERROR: check peer STA MAC, node IDs, channel and keys; motor commands rejected");
}

void subscribeEspNowMotorTopics() {
  if (!RELAY_MOTOR_BRIDGE_ENABLED) return;
  for (size_t i = 0; i < peerCount; ++i)
    for (size_t m = 0; m < 2; ++m) client.subscribe(ESPNOW_ROUTES[i].topics[m], 0);
}

bool routeEspNowMotorCommand(const char* topic, const uint8_t* payload, size_t length) {
  if (!RELAY_MOTOR_BRIDGE_ENABLED) return false;
  for (size_t i = 0; i < peerCount; ++i) {
    for (size_t m = 0; m < 2; ++m) {
      if (strcmp(topic, ESPNOW_ROUTES[i].topics[m])) continue;
      if (!radioReady || suspended || !peers[i]->link.enqueue(museum::Target(m + 1), payload, length, m + 1, millis()))
        feedback(topic, false);
      return true;
    }
  }
  return false;
}

void stopEspNowMotors(bool withFeedback) {
  if (!RELAY_MOTOR_BRIDGE_ENABLED) return;
  if (stopWaiting) { stopWaiting = false; stopFeedback(false); }
  // Cancel the preceding batch before arming the aggregate completion counter.
  for (size_t i = 0; i < peerCount; ++i) peers[i]->link.stop(0, millis());
  if (!initialized || !peerCount) { if (withFeedback) stopFeedback(false); return; }
  stopWaiting = withFeedback; stopOk = true; stopRemaining = uint8_t(peerCount);
  for (size_t i = 0; i < peerCount; ++i)
    peers[i]->link.stop(withFeedback ? StopCookie : 0, millis());
}

void suspendEspNowBridge() {
  suspended = true;
  for (size_t i = 0; i < peerCount; ++i) peers[i]->link.setAvailable(false, millis());
  stopEspNowMotors(false);
  espNowBridgeLoop();
}

void espNowBridgeLoop() {
  if (!RELAY_MOTOR_BRIDGE_ENABLED) return;
  const bool mqtt = isMqttConnected();
  const bool ready = initialized && isEspNowNetworkReady() && radio.healthy();
  if (ready != radioReady) {
    radioReady = ready;
    Serial.println(ready ? "ESP-NOW radio ready: synchronizing motor link" :
        "ESP-NOW radio unavailable: motor control disabled while connection recovers");
  }
  const uint32_t now = millis();
  for (size_t i = 0; i < peerCount; ++i)
    peers[i]->link.setAvailable(mqtt && radioReady && !suspended, now);
  museum::RadioEvent event;
  while (radioReady && radio.poll(event)) peers[event.peer]->link.receive(event.frame, millis());
  for (size_t i = 0; i < peerCount; ++i) {
    peers[i]->link.tick(millis());
    if (mqtt && !suspended) peers[i]->publish(millis(), !mqttWasConnected);
  }
  mqttWasConnected = mqtt;
}
