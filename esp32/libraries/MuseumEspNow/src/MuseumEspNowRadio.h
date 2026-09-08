#pragma once

#include "MuseumEspNow.h"
#include <Arduino.h>
#include <esp_now.h>
#include <esp_idf_version.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

namespace museum {

constexpr size_t MaxPeers = 4;
struct RadioPeer {
  uint8_t mac[6];
  uint16_t node;
  bool encrypted;
  uint8_t key[16];
};
struct RadioEvent {
  Frame frame;
  uint32_t receivedAt;
  uint8_t peer;
};

class Radio {
 public:
  bool begin(uint8_t channel, uint16_t self, const RadioPeer* peers, size_t count,
             const uint8_t* pmk = nullptr);
  bool send(size_t peer, const Frame& frame);
  bool poll(RadioEvent& event);
  bool healthy();
  static bool validMac(const uint8_t* mac);

 private:
  static Radio* instance_;
  const RadioPeer* peers_ = nullptr;
  size_t count_ = 0;
  uint16_t self_ = 0;
  uint8_t mac_[6] = {}, channel_ = 0;
  bool initialized_ = false;
  portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;
  bool busy_ = false;
  uint32_t sentAt_ = 0;
  StaticQueue_t rxStorage_, stopStorage_;
  uint8_t rxBytes_[8 * sizeof(RadioEvent)];
  uint8_t stopBytes_[4 * sizeof(RadioEvent)];
  QueueHandle_t rx_ = nullptr, stops_ = nullptr;
  static void received(const esp_now_recv_info_t* info, const uint8_t* data, int length);
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
  static void sent(const esp_now_send_info_t* info, esp_now_send_status_t status);
#else
  static void sent(const uint8_t* mac, esp_now_send_status_t status);
#endif
};

class PeerSender : public Sender {
 public:
  PeerSender(Radio& radio, size_t index) : radio_(radio), index_(index) {}
  bool send(const Frame& frame) override { return radio_.send(index_, frame); }
 private:
  Radio& radio_;
  size_t index_;
};

}  // namespace museum
