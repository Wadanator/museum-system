#include "MuseumEspNow.h"

namespace museum {

bool isStop(const Frame& f) {
  return f.kind == Kind::Command && f.target == Target::All &&
         f.length == 4 && memcmp(f.payload, "STOP", 4) == 0;
}

bool validFrame(const Frame& f) {
  if (!f.source || !f.destination || !f.session || !f.seq || f.length > PayloadSize)
    return false;
  switch (f.kind) {
    case Kind::Probe:
      return f.target == Target::None && f.result == Result::None &&
             f.length == 1 && f.payload[0] <= 1;
    case Kind::Hello:
    case Kind::Ack: {
      Snapshot state;
      if (!f.epoch || !readSnapshot(f, state)) return false;
      if (f.kind == Kind::Hello)
        return f.target == Target::None && f.result == Result::None;
      return f.target >= Target::Motor1 && f.target <= Target::All &&
             (f.result == Result::Ok || f.result == Result::Error);
    }
    case Kind::Command:
      return f.result == Result::None && f.length > 0 && f.length < PayloadSize &&
             memchr(f.payload, 0, f.length) == nullptr &&
             ((f.target == Target::Motor1 || f.target == Target::Motor2) || isStop(f));
  }
  return false;
}

size_t encode(const Frame& f, uint8_t* out, size_t capacity) {
  const size_t size = HeaderSize + f.length + 2;
  if (!out || !validFrame(f) || capacity < size) return 0;
  out[0] = 0x4d; out[1] = 0x53; out[2] = 1; out[3] = uint8_t(f.kind);
  out[4] = uint8_t(f.source); out[5] = uint8_t(f.source >> 8);
  out[6] = uint8_t(f.destination); out[7] = uint8_t(f.destination >> 8);
  put32(out + 8, f.session); put32(out + 12, f.epoch); put32(out + 16, f.seq);
  out[20] = uint8_t(f.target); out[21] = uint8_t(f.result); out[22] = f.length;
  memcpy(out + HeaderSize, f.payload, f.length);
  const uint16_t crc = crc16(out, size - 2);
  out[size - 2] = uint8_t(crc); out[size - 1] = uint8_t(crc >> 8);
  return size;
}

bool decode(const uint8_t* p, size_t size, Frame& out) {
  if (!p || size < HeaderSize + 2 || size > MaxFrameSize ||
      p[0] != 0x4d || p[1] != 0x53 || p[2] != 1 ||
      p[22] > PayloadSize || size != HeaderSize + p[22] + 2) return false;
  const uint16_t expected = uint16_t(p[size - 2]) | (uint16_t(p[size - 1]) << 8);
  if (crc16(p, size - 2) != expected) return false;
  Frame f;
  f.kind = Kind(p[3]); f.source = uint16_t(p[4]) | (uint16_t(p[5]) << 8);
  f.destination = uint16_t(p[6]) | (uint16_t(p[7]) << 8);
  f.session = get32(p + 8); f.epoch = get32(p + 12); f.seq = get32(p + 16);
  f.target = Target(p[20]); f.result = Result(p[21]); f.length = p[22];
  memcpy(f.payload, p + HeaderSize, f.length);
  if (!validFrame(f)) return false;
  out = f;
  return true;
}

void writeSnapshot(Frame& f, const Snapshot& state) {
  f.length = 10;
  put32(f.payload, state.revision);
  for (unsigned i = 0; i < 2; ++i) {
    f.payload[4 + i * 3] = state.motors[i].on;
    f.payload[5 + i * 3] = state.motors[i].speed;
    f.payload[6 + i * 3] = uint8_t(state.motors[i].direction);
  }
}

bool readSnapshot(const Frame& f, Snapshot& state) {
  if (f.length != 10) return false;
  state.revision = get32(f.payload);
  for (unsigned i = 0; i < 2; ++i) {
    auto& m = state.motors[i];
    m.on = f.payload[4 + i * 3]; m.speed = f.payload[5 + i * 3];
    m.direction = char(f.payload[6 + i * 3]);
    if (m.on > 1 || m.speed > 100 || (!m.on && m.speed != 0) ||
        (m.direction != 'L' && m.direction != 'R' && m.direction != 'S')) return false;
  }
  return true;
}

bool Timing::valid() const {
  return ackMs >= 100 && ackMs <= 500 && retryMs >= 20 && retryMs < ackMs &&
         attempts >= 1 && attempts <= 5 && heartbeatMs >= 250 &&
         heartbeatMs <= 1000 && masterTimeoutMs >= heartbeatMs * 2 &&
         masterTimeoutMs <= 5000 && offlineMs >= masterTimeoutMs && offlineMs <= 10000;
}

MasterLink::MasterLink(Sender& sender, MasterEvents& events, uint16_t self,
                       uint16_t peer, uint32_t session, Timing timing)
    : sender_(sender), events_(events), self_(self), peer_(peer),
      session_(session ? session : 1), timing_(timing) {}

bool MasterLink::online(uint32_t now) const {
  return seen_ && elapsed(now, lastSeen_) < timing_.offlineMs;
}

void MasterLink::cancel() {
  if (active_ && pending_.cookie) events_.completed(pending_.cookie, false);
  active_ = false;
  for (size_t i = 0; i < count_; ++i)
    if (queue_[i].cookie) events_.completed(queue_[i].cookie, false);
  count_ = 0;
}

void MasterLink::start(Request request) {
  request.frame.kind = Kind::Command;
  request.frame.source = self_; request.frame.destination = peer_;
  request.frame.session = session_; request.frame.epoch = epoch_;
  request.frame.seq = nextSequence(sequence_);
  pending_ = request; active_ = true;
}

void MasterLink::setAvailable(bool available, uint32_t now) {
  if (available == available_) return;
  available_ = available;
  stop(0, now);
  probed_ = false;
}

bool MasterLink::enqueue(Target target, const uint8_t* command, size_t length,
                         uint32_t cookie, uint32_t now) {
  if (!ready() || !online(now) || count_ == 8 || !command ||
      length == 0 || length >= PayloadSize || memchr(command, 0, length) ||
      (target != Target::Motor1 && target != Target::Motor2)) return false;
  Request r;
  r.frame.target = target; r.frame.length = uint8_t(length);
  memcpy(r.frame.payload, command, length);
  r.cookie = cookie; r.created = now;
  queue_[count_++] = r;
  return true;
}

void MasterLink::stop(uint32_t cookie, uint32_t now) {
  cancel(); ready_ = false;
  Request r;
  r.frame.target = Target::All; r.frame.length = 4;
  memcpy(r.frame.payload, "STOP", 4);
  r.created = now; r.cookie = cookie;
  start(r);
}

void MasterLink::acceptSnapshot(const Frame& frame) {
  Snapshot state;
  if (readSnapshot(frame, state) &&
      (!snapshotSeen_ || newer(state.revision, lastRevision_))) {
    snapshotSeen_ = true; lastRevision_ = state.revision;
    events_.snapshot(state);
  }
}

void MasterLink::receive(const Frame& f, uint32_t now) {
  if (!validFrame(f) || f.source != peer_ || f.destination != self_ ||
      f.session != session_) return;
  if (f.kind == Kind::Hello) {
    if (!awaitingProbe_ || f.seq != probeSequence_ ||
        elapsed(now, lastProbe_) >= timing_.ackMs) return;
    awaitingProbe_ = false; seen_ = true; lastSeen_ = now;
    peerEnabled_ = probeEnabled_;
    if (f.epoch != epoch_) {
      // Preserve an explicitly requested STOP across initial lease discovery.
      uint32_t cookie = active_ && isStop(pending_.frame) ? pending_.cookie : 0;
      const uint32_t created = active_ ? pending_.created : now;
      if (cookie) pending_.cookie = 0;
      epoch_ = f.epoch; snapshotSeen_ = false;
      stop(cookie, now);
      if (cookie) pending_.created = created;
    } else if (!ready_ && !active_ && available_ && peerEnabled_) {
      stop(0, now);
    }
    if (available_ && !peerEnabled_) probed_ = false;
    acceptSnapshot(f);
  } else if (f.kind == Kind::Ack) {
    if (!active_ || f.epoch != epoch_ || f.seq != pending_.frame.seq ||
        f.target != pending_.frame.target ||
        elapsed(now, pending_.created) >= timing_.ackMs) return;
    seen_ = true; lastSeen_ = now;
    const bool ok = f.result == Result::Ok;
    if (isStop(pending_.frame)) ready_ = ok && available_ && peerEnabled_;
    const uint32_t cookie = pending_.cookie;
    active_ = false;
    acceptSnapshot(f);
    if (cookie) events_.completed(cookie, ok);
  }
}

void MasterLink::tick(uint32_t now) {
  if (seen_ && !online(now)) {
    seen_ = false; epoch_ = 0; snapshotSeen_ = false;
    stop(0, now);
  }
  // Queue residence is part of the MQTT ACK budget, not an extra delay.
  while (count_ && elapsed(now, queue_[0].created) >= timing_.ackMs) {
    if (queue_[0].cookie) events_.completed(queue_[0].cookie, false);
    for (size_t i = 1; i < count_; ++i) queue_[i - 1] = queue_[i];
    --count_;
  }
  if (active_ && elapsed(now, pending_.created) >= timing_.ackMs) {
    const bool wasStop = isStop(pending_.frame);
    if (pending_.cookie) events_.completed(pending_.cookie, false);
    active_ = false; ready_ = false;
    if (!wasStop) stop(0, now);
  }
  if (!active_ && count_ && ready()) {
    Request r = queue_[0];
    for (size_t i = 1; i < count_; ++i) queue_[i - 1] = queue_[i];
    --count_; start(r);
  }
  if (active_ && epoch_ && pending_.attempts < timing_.attempts &&
      (!pending_.attempts || elapsed(now, pending_.sent) >= timing_.retryMs)) {
    pending_.frame.epoch = epoch_;
    if (sender_.send(pending_.frame)) {
      pending_.sent = now; ++pending_.attempts;
    }
  }
  if (!probed_ || elapsed(now, lastProbe_) >= timing_.heartbeatMs) {
    Frame f;
    f.source = self_; f.destination = peer_; f.session = session_;
    f.epoch = epoch_; f.seq = probeSequence_ + 1;
    if (!f.seq) f.seq = 1;
    f.length = 1; f.payload[0] = available_ && online(now) ? 1 : 0;
    if (sender_.send(f)) {
      probeSequence_ = f.seq; lastProbe_ = now; probed_ = true; awaitingProbe_ = true;
      probeEnabled_ = f.payload[0] != 0;
    }
  }
}

MotorLink::MotorLink(Sender& sender, MotorActions& actions, uint16_t self,
                     uint16_t master, Timing timing)
    : sender_(sender), actions_(actions), self_(self), master_(master), timing_(timing) {}

void MotorLink::invalidate() {
  actions_.hardStop();
  const uint32_t old = epoch_;
  epoch_ = actions_.nonce();
  if (!epoch_ || epoch_ == old) epoch_ = old + 1;
  if (!epoch_) epoch_ = 1;
  synced_ = false; enabled_ = false; contact_ = false;
  lastSequence_ = 0; revision_ = 0;
}

void MotorLink::suspend() { suspended_ = true; invalidate(); }

void MotorLink::reply(const Frame& request, Kind kind, Result result) {
  Frame f;
  f.kind = kind; f.source = self_; f.destination = master_;
  f.session = request.session; f.epoch = epoch_; f.seq = request.seq;
  f.target = kind == Kind::Ack ? request.target : Target::None; f.result = result;
  Snapshot state = actions_.snapshot();
  state.revision = nextSequence(revision_);
  writeSnapshot(f, state);
  sender_.send(f);  // A lost ACK is recovered by a duplicate command retry.
}

void MotorLink::receive(const Frame& f, uint32_t now) {
  if (suspended_ || !validFrame(f) || f.source != master_ || f.destination != self_)
    return;
  tick(now);  // Expire a lease before examining queued commands.
  if (f.kind == Kind::Probe) {
    if (f.session != session_) {
      invalidate(); session_ = f.session; lastProbe_ = 0;
    }
    if (!newer(f.seq, lastProbe_)) return;
    lastProbe_ = f.seq;
    if (!epoch_) invalidate();
    if (!f.payload[0] && enabled_) invalidate();
    enabled_ = f.payload[0] != 0;
    contact_ = true; lastContact_ = now;
    reply(f, Kind::Hello, Result::None);
    return;
  }
  if (f.kind != Kind::Command || f.session != session_ || f.epoch != epoch_ || !epoch_)
    return;
  if (f.seq == lastSequence_) {
    if (f.target == lastCommand_.target && f.length == lastCommand_.length &&
        memcmp(f.payload, lastCommand_.payload, f.length) == 0)
      reply(f, Kind::Ack, lastResult_);
    return;
  }
  if (!newer(f.seq, lastSequence_)) return;
  bool ok = false;
  if (isStop(f)) {
    actions_.hardStop(); synced_ = true; ok = true;
  } else if (synced_ && enabled_) {
    char command[PayloadSize];
    memcpy(command, f.payload, f.length); command[f.length] = 0;
    ok = actions_.execute(f.target, command);
  }
  lastSequence_ = f.seq; lastCommand_ = f;
  lastResult_ = ok ? Result::Ok : Result::Error;
  contact_ = true; lastContact_ = now;
  reply(f, Kind::Ack, lastResult_);
}

void MotorLink::tick(uint32_t now) {
  if (contact_ && elapsed(now, lastContact_) >= timing_.masterTimeoutMs) invalidate();
}

}  // namespace museum
