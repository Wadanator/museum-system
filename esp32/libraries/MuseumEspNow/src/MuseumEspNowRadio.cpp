#include "MuseumEspNowRadio.h"
#include <WiFi.h>
#include <esp_wifi.h>

namespace museum {

Radio* Radio::instance_ = nullptr;

bool Radio::validMac(const uint8_t* mac) {
  static const uint8_t zero[6] = {};
  return mac && !(mac[0] & 1) && memcmp(mac, zero, 6) != 0;
}

bool Radio::begin(uint8_t channel, uint16_t self, const RadioPeer* peers,
                  size_t count, const uint8_t* pmk) {
  if (instance_ || !self || channel < 1 || channel > 13 || !peers ||
      !count || count > MaxPeers) return false;
  // Initialize before AP association; a master may later join an AP on this channel.
  WiFi.persistent(false);
  if (!WiFi.mode(WIFI_STA)) {
    Serial.println("ESP-NOW INIT ERROR: cannot start WiFi STA");
    return false;
  }
  WiFi.setAutoReconnect(false);
  WiFi.disconnect(false, false);
  const esp_err_t macResult = esp_wifi_get_mac(WIFI_IF_STA, mac_);
  if (macResult != ESP_OK || !validMac(mac_)) {
    Serial.printf("ESP-NOW INIT ERROR: cannot read STA MAC (%s)\n",
                  esp_err_to_name(macResult));
    return false;
  }
  Serial.printf("ESP-NOW STA MAC %02X:%02X:%02X:%02X:%02X:%02X, channel %u\n",
                mac_[0], mac_[1], mac_[2], mac_[3], mac_[4], mac_[5], channel);
  for (size_t i = 0; i < count; ++i) {
    if (!validMac(peers[i].mac) || memcmp(peers[i].mac, mac_, 6) == 0 ||
        !peers[i].node || peers[i].node == self) return false;
    for (size_t j = 0; j < i; ++j)
      if (peers[i].node == peers[j].node || memcmp(peers[i].mac, peers[j].mac, 6) == 0)
        return false;
    if (peers[i].encrypted) {
      uint8_t keyBits = 0, pmkBits = 0;
      for (size_t j = 0; j < 16; ++j) {
        keyBits |= peers[i].key[j];
        if (pmk) pmkBits |= pmk[j];
      }
      if (!keyBits || !pmkBits) return false;
    }
  }
  if (esp_wifi_set_ps(WIFI_PS_NONE) != ESP_OK ||
      esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE) != ESP_OK ||
      esp_now_init() != ESP_OK) return false;
  if (pmk && esp_now_set_pmk(pmk) != ESP_OK) { esp_now_deinit(); return false; }
  for (size_t i = 0; i < count; ++i) {
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, peers[i].mac, 6);
    peer.channel = channel; peer.ifidx = WIFI_IF_STA; peer.encrypt = peers[i].encrypted;
    memcpy(peer.lmk, peers[i].key, 16);
    if (esp_now_add_peer(&peer) != ESP_OK) { esp_now_deinit(); return false; }
  }
  peers_ = peers; count_ = count; self_ = self; channel_ = channel;
  rx_ = xQueueCreateStatic(8, sizeof(RadioEvent), rxBytes_, &rxStorage_);
  stops_ = xQueueCreateStatic(4, sizeof(RadioEvent), stopBytes_, &stopStorage_);
  instance_ = this;
  if (esp_now_register_recv_cb(received) != ESP_OK || esp_now_register_send_cb(sent) != ESP_OK) {
    esp_now_deinit(); instance_ = nullptr; return false;
  }
  initialized_ = true;
  return true;
}

bool Radio::healthy() {
  if (!initialized_) return false;
  uint8_t channel = 0;
  wifi_second_chan_t secondary;
  if (esp_wifi_get_channel(&channel, &secondary) != ESP_OK || channel != channel_) return false;
  portENTER_CRITICAL(&mux_);
  const bool stalled = busy_ && elapsed(millis(), sentAt_) > 250;
  portEXIT_CRITICAL(&mux_);
  return !stalled;
}

bool Radio::send(size_t peer, const Frame& frame) {
  if (peer >= count_ || !healthy()) return false;
  uint8_t bytes[MaxFrameSize];
  const size_t length = encode(frame, bytes, sizeof(bytes));
  if (!length) return false;
  portENTER_CRITICAL(&mux_);
  if (busy_) { portEXIT_CRITICAL(&mux_); return false; }
  busy_ = true; sentAt_ = millis();
  portEXIT_CRITICAL(&mux_);
  if (esp_now_send(peers_[peer].mac, bytes, length) == ESP_OK) return true;
  portENTER_CRITICAL(&mux_);
  busy_ = false;
  portEXIT_CRITICAL(&mux_);
  return false;
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
void Radio::sent(const esp_now_send_info_t*, esp_now_send_status_t) {
#else
void Radio::sent(const uint8_t*, esp_now_send_status_t) {
#endif
  Radio* r = instance_;
  if (!r) return;
  portENTER_CRITICAL(&r->mux_);
  r->busy_ = false;
  portEXIT_CRITICAL(&r->mux_);
}

void Radio::received(const esp_now_recv_info_t* info, const uint8_t* data, int length) {
  Radio* r = instance_;
  if (!r || !info || length < 0 || memcmp(info->des_addr, r->mac_, 6) != 0) return;
  for (size_t i = 0; i < r->count_; ++i) {
    if (memcmp(info->src_addr, r->peers_[i].mac, 6) != 0) continue;
    RadioEvent event;
    if (!decode(data, size_t(length), event.frame) || event.frame.source != r->peers_[i].node ||
        event.frame.destination != r->self_) return;
    event.peer = uint8_t(i); event.receivedAt = millis();
    // Reserved STOP capacity prevents an ordinary command burst from starving it.
    xQueueSend(isStop(event.frame) ? r->stops_ : r->rx_, &event, 0);
    return;
  }
}

bool Radio::poll(RadioEvent& event) {
  if (!initialized_) return false;
  while (xQueueReceive(stops_, &event, 0) == pdTRUE || xQueueReceive(rx_, &event, 0) == pdTRUE) {
    if (elapsed(millis(), event.receivedAt) <= 100) return true;
  }
  return false;
}

}  // namespace museum
