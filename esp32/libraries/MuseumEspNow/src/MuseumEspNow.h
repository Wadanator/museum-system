#pragma once

#include <stdint.h>
#include <stddef.h>
#include <string.h>

namespace museum {

constexpr size_t PayloadSize = 64;
constexpr size_t HeaderSize = 23;
constexpr size_t MaxFrameSize = HeaderSize + PayloadSize + 2;
static_assert(MaxFrameSize < 200, "ESP-NOW v1 compatible frame");

enum class Kind : uint8_t { Probe = 1, Hello = 2, Command = 3, Ack = 4 };
enum class Target : uint8_t { None = 0, Motor1 = 1, Motor2 = 2, All = 3 };
enum class Result : uint8_t { None = 0, Ok = 1, Error = 2 };

struct Frame {
  Kind kind = Kind::Probe;
  uint16_t source = 0;
  uint16_t destination = 0;
  uint32_t session = 0;  // Master boot nonce, echoed by the motor.
  uint32_t epoch = 0;    // Motor lease nonce; rotated on link loss/restart.
  uint32_t seq = 0;
  Target target = Target::None;
  Result result = Result::None;
  uint8_t length = 0;
  uint8_t payload[PayloadSize] = {};
};

inline uint32_t elapsed(uint32_t now, uint32_t since) { return now - since; }
inline bool newer(uint32_t a, uint32_t b) { return a != b && uint32_t(a - b) < 0x80000000UL; }
inline uint32_t nextSequence(uint32_t& value) { if (++value == 0) ++value; return value; }
inline void put32(uint8_t* p, uint32_t v) {
  for (unsigned i = 0; i < 4; ++i) p[i] = uint8_t(v >> (8 * i));
}
inline uint32_t get32(const uint8_t* p) {
  uint32_t v = 0;
  for (unsigned i = 0; i < 4; ++i) v |= uint32_t(p[i]) << (8 * i);
  return v;
}
inline uint16_t crc16(const uint8_t* p, size_t size) {
  uint16_t crc = 0xffff;
  while (size--) {
    crc ^= uint16_t(*p++) << 8;
    for (unsigned bit = 0; bit < 8; ++bit)
      crc = (crc & 0x8000) ? uint16_t((crc << 1) ^ 0x1021) : uint16_t(crc << 1);
  }
  return crc;
}

size_t encode(const Frame& frame, uint8_t* output, size_t capacity);
bool decode(const uint8_t* data, size_t length, Frame& output);
bool validFrame(const Frame& frame);
bool isStop(const Frame& frame);

struct MotorSnapshot {
  uint8_t on = 0;
  uint8_t speed = 0;
  char direction = 'S';
};
struct Snapshot {
  uint32_t revision = 0;
  MotorSnapshot motors[2];
};
void writeSnapshot(Frame& frame, const Snapshot& state);
bool readSnapshot(const Frame& frame, Snapshot& state);

struct Timing {
  uint32_t ackMs = 450;
  uint32_t retryMs = 80;
  uint32_t heartbeatMs = 1000;
  uint32_t offlineMs = 3500;
  uint32_t masterTimeoutMs = 3000;
  uint8_t attempts = 4;
  bool valid() const;
};

class Sender {
 public:
  virtual ~Sender() = default;
  virtual bool send(const Frame& frame) = 0;
};

class MasterEvents {
 public:
  virtual ~MasterEvents() = default;
  virtual void completed(uint32_t cookie, bool accepted) = 0;
  virtual void snapshot(const Snapshot& state) = 0;
};

// One ordered command stream per peer, reusable by any MQTT or other master.
class MasterLink {
 public:
  MasterLink(Sender& sender, MasterEvents& events, uint16_t self, uint16_t peer,
             uint32_t session, Timing timing = Timing());
  void setAvailable(bool available, uint32_t now);
  bool enqueue(Target target, const uint8_t* command, size_t length,
               uint32_t cookie, uint32_t now);
  void stop(uint32_t cookie, uint32_t now);
  void receive(const Frame& frame, uint32_t now);
  void tick(uint32_t now);
  bool online(uint32_t now) const;
  bool ready() const { return ready_ && available_; }

 private:
  struct Request {
    Frame frame;
    uint32_t cookie = 0;
    uint32_t created = 0;
    uint32_t sent = 0;
    uint8_t attempts = 0;
  };
  Sender& sender_;
  MasterEvents& events_;
  uint16_t self_, peer_;
  uint32_t session_, epoch_ = 0, sequence_ = 0, probeSequence_ = 0;
  Timing timing_;
  Request queue_[8], pending_;
  size_t count_ = 0;
  bool active_ = false, available_ = false, ready_ = false, seen_ = false;
  bool probed_ = false, awaitingProbe_ = false, snapshotSeen_ = false;
  bool probeEnabled_ = false, peerEnabled_ = false;
  uint32_t lastProbe_ = 0, lastSeen_ = 0, lastRevision_ = 0;
  void cancel();
  void acceptSnapshot(const Frame& frame);
  void start(Request request);
};

class MotorActions {
 public:
  virtual ~MotorActions() = default;
  virtual bool execute(Target target, const char* command) = 0;
  virtual void hardStop() = 0;
  virtual Snapshot snapshot() = 0;
  virtual uint32_t nonce() = 0;
};

class MotorLink {
 public:
  MotorLink(Sender& sender, MotorActions& actions, uint16_t self, uint16_t master,
            Timing timing = Timing());
  void receive(const Frame& frame, uint32_t now);
  void tick(uint32_t now);
  void suspend();
  bool linked() const { return synced_ && enabled_; }

 private:
  Sender& sender_;
  MotorActions& actions_;
  uint16_t self_, master_;
  Timing timing_;
  uint32_t session_ = 0, epoch_ = 0, lastSequence_ = 0, lastProbe_ = 0;
  uint32_t lastContact_ = 0, revision_ = 0;
  bool synced_ = false, enabled_ = false, contact_ = false, suspended_ = false;
  Result lastResult_ = Result::Error;
  Frame lastCommand_;
  void invalidate();
  void reply(const Frame& request, Kind kind, Result result);
};

}  // namespace museum
