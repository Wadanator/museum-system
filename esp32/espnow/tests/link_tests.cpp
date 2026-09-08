#include <MuseumEspNow.h>
#include <MuseumMotorCommand.h>
#include <cassert>
#include <cstdio>
#include <deque>
#include <vector>
#include <utility>

using namespace museum;

struct Pipe : Sender {
  std::deque<Frame> frames;
  bool transmit = true;
  bool send(const Frame& f) override { if (transmit) frames.push_back(f); return transmit; }
};
struct Events : MasterEvents {
  std::vector<std::pair<uint32_t, bool>> results;
  Snapshot state;
  void completed(uint32_t cookie, bool ok) override { results.emplace_back(cookie, ok); }
  void snapshot(const Snapshot& s) override { state = s; }
};
struct Motors : MotorActions {
  unsigned executions = 0, stops = 0;
  uint32_t counter = 100;
  Snapshot state;
  bool execute(Target target, const char* command) override {
    ++executions;
    auto& m = state.motors[target == Target::Motor1 ? 0 : 1];
    if (!strcmp(command, "BAD")) return false;
    m.on = strcmp(command, "OFF") != 0; m.speed = m.on ? 50 : 0; m.direction = m.on ? 'L' : 'S';
    return true;
  }
  void hardStop() override { ++stops; state = Snapshot(); }
  Snapshot snapshot() override { return state; }
  uint32_t nonce() override { return ++counter; }
};
struct Rig {
  Pipe downstream, upstream;
  Events events;
  Motors motors;
  MasterLink master{downstream, events, 1, 2, 40};
  MotorLink slave{upstream, motors, 2, 1};
  uint32_t now = 0;
  bool dropDown = false, dropUp = false, dropAck = false;
  void step(uint32_t amount = 10) {
    now += amount;
    master.tick(now); slave.tick(now);
    while (!downstream.frames.empty()) {
      Frame f = downstream.frames.front(); downstream.frames.pop_front();
      if (!dropDown) slave.receive(f, now);
    }
    while (!upstream.frames.empty()) {
      Frame f = upstream.frames.front(); upstream.frames.pop_front();
      if (!dropUp && !(dropAck && f.kind == Kind::Ack)) master.receive(f, now);
    }
  }
  void run(uint32_t duration) { for (uint32_t t = 0; t < duration; t += 10) step(); }
  void connect() {
    master.setAvailable(true, now); run(1500);
    assert(master.ready()); assert(master.online(now)); assert(slave.linked());
  }
  bool command(const char* command, uint32_t cookie = 10, Target target = Target::Motor1) {
    return master.enqueue(target, reinterpret_cast<const uint8_t*>(command), strlen(command), cookie, now);
  }
};

static void codec() {
  Frame f;
  f.kind = Kind::Command; f.source = 1; f.destination = 2; f.session = 40;
  f.epoch = 50; f.seq = 123; f.target = Target::Motor1; f.length = 9;
  memcpy(f.payload, "ON:50:L:0", f.length);
  uint8_t bytes[MaxFrameSize];
  const size_t size = encode(f, bytes, sizeof(bytes));
  assert(size == HeaderSize + 11);
  Frame decoded;
  assert(decode(bytes, size, decoded)); assert(decoded.seq == f.seq);
  assert(!decode(bytes, size - 1, decoded));
  assert(!decode(bytes, size + 1, decoded));
  for (size_t i = 0; i < size; ++i) {
    bytes[i] ^= 1; assert(!decode(bytes, size, decoded)); bytes[i] ^= 1;
  }
  f.length = 64; assert(!encode(f, bytes, sizeof(bytes)));
  f.length = 4; f.target = Target::All; memcpy(f.payload, "STOP", 4);
  assert(encode(f, bytes, sizeof(bytes))); assert(isStop(f));
  assert(newer(1, 0xffffffffUL)); assert(!newer(0xffffffffUL, 1));
  assert(Timing().valid());
  Timing invalid; invalid.retryMs = 0; assert(!invalid.valid());
}

static void normalAndDuplicates() {
  Rig r; r.connect();
  assert(r.command("ON:50:L:0")); r.run(100);
  assert(r.motors.executions == 1); assert(r.events.state.motors[0].on);
  assert(r.events.results.back() == std::make_pair(uint32_t(10), true));
  r.dropAck = true;
  assert(r.command("OFF", 11)); r.run(180);
  assert(r.motors.executions == 2);
  r.dropAck = false; r.run(100);
  assert(r.events.results.back() == std::make_pair(uint32_t(11), true));
  assert(r.motors.executions == 2); assert(!r.events.state.motors[0].on);
  assert(r.command("BAD", 12)); r.run(50);
  assert(r.events.results.back() == std::make_pair(uint32_t(12), false));
}

static void motorParser() {
  MotorCommand parsed;
  const char* valid[] = {"ON:100:L:10000", "ON:100:R:10000", "ON:1:l", "OFF", "SPEED:0", "SPEED:50", "DIR:R", "DIR:l"};
  for (const char* cmd : valid) assert(parseMotorCommand(cmd, 180000, parsed));
  const char* invalid[] = {"", "ON", "ON::L", "ON:0:L", "ON:101:L", "ON:-1:L", "ON:50:LEFT",
      "ON:50:L:-1", "ON:50:L:180001", "ON:50:L:10:x", "OFF:x", "DIR:", "DIR:Q", "SPEED:",
      "SPEED:50junk", "SPEED:99999999999999999999999999", "ON:1:L:"};
  for (const char* cmd : invalid) assert(!parseMotorCommand(cmd, 180000, parsed));
  assert(parseMotorCommand("ON:0050:L:0002000", 180000, parsed));
  assert(!strcmp(parsed.speed, "50")); assert(!strcmp(parsed.ramp, "2000"));
}

static void stopBarrier() {
  Rig r; r.connect();
  assert(r.command("ON:50:L:0"));
  r.master.tick(r.now);
  Frame old = r.downstream.frames.front(); r.downstream.frames.clear();
  r.master.stop(20, r.now); r.run(50);
  const unsigned before = r.motors.executions;
  r.slave.receive(old, r.now);
  assert(r.motors.executions == before); assert(!r.motors.state.motors[0].on);
  assert(r.events.results.back() == std::make_pair(uint32_t(20), true));
  r.slave.receive(old, r.now + 1); assert(r.motors.executions == before);
}

static void timeoutAndEpoch() {
  Rig r; r.connect(); assert(r.command("ON:50:L:0"));
  r.master.tick(r.now);
  const Frame old = r.downstream.frames.front();
  r.run(50); assert(r.motors.state.motors[0].on);
  r.dropDown = true; r.run(3010);
  assert(!r.motors.state.motors[0].on); assert(!r.slave.linked());
  r.slave.receive(old, r.now); assert(!r.motors.state.motors[0].on);
  r.dropDown = false; r.run(2000);
  assert(r.master.ready()); assert(!r.motors.state.motors[0].on);
  r.slave.receive(old, r.now); assert(!r.motors.state.motors[0].on);
}

static void oneWayAndBrokerLoss() {
  Rig r; r.connect(); assert(r.command("ON:50:L:0")); r.run(100);
  r.dropUp = true; r.run(4700);
  assert(!r.motors.state.motors[0].on); assert(!r.master.online(r.now));
  r.dropUp = false; r.run(2000); assert(r.master.ready());
  assert(r.command("ON:50:L:0")); r.run(100);
  r.master.setAvailable(false, r.now); r.run(100);
  assert(!r.motors.state.motors[0].on); assert(!r.master.ready());
  assert(!r.command("ON:50:L:0"));
  r.master.setAvailable(true, r.now); r.run(2000);
  assert(r.master.ready()); assert(!r.motors.state.motors[0].on);
}

static void queueBudgetAndLostAck() {
  Rig r; r.connect(); r.dropAck = true;
  for (unsigned i = 0; i < 8; ++i) assert(r.command("ON:50:L:0", i + 1));
  assert(!r.command("ON:50:L:0", 9));
  r.run(500);
  assert(r.events.results.size() == 8);
  for (const auto& result : r.events.results) assert(!result.second);
  // Failure of the first command cancels the remaining work and sends STOP.
  assert(r.motors.executions == 1); assert(!r.motors.state.motors[0].on);
}

static void rebootAndWrongPeer() {
  Rig r; r.connect(); assert(r.command("ON:50:L:0")); r.run(100);
  Pipe freshDown;
  MasterLink freshMaster(freshDown, r.events, 1, 2, 999);
  freshMaster.setAvailable(true, r.now); freshMaster.tick(r.now);
  for (const auto& frame : freshDown.frames) r.slave.receive(frame, r.now);
  assert(!r.motors.state.motors[0].on);
  assert(!r.slave.linked());
  Frame rogue;
  rogue.source = 55; rogue.destination = 2; rogue.session = 1;
  rogue.seq = 1; rogue.length = 1; rogue.payload[0] = 1;
  const unsigned stops = r.motors.stops;
  r.slave.receive(rogue, r.now); assert(r.motors.stops == stops);
}

static void clockRollover() {
  Rig r; r.now = 0xfffffc00UL; r.connect();
  assert(r.command("ON:50:L:0")); r.run(100);
  r.dropDown = true; r.run(3100); assert(!r.motors.state.motors[0].on);
}

static void slaveRestartAndStaleReplies() {
  Rig r; r.connect(); assert(r.command("ON:50:L:0"));
  r.master.tick(r.now);
  Frame oldCommand = r.downstream.frames.front();
  r.run(100); assert(r.motors.state.motors[0].on);
  r.motors.hardStop();
  MotorLink rebooted(r.upstream, r.motors, 2, 1);
  rebooted.receive(oldCommand, r.now);
  assert(!r.motors.state.motors[0].on);
  r.now += 1000; r.master.tick(r.now);
  Frame hello;
  for (const auto& f : r.downstream.frames) rebooted.receive(f, r.now);
  for (const auto& f : r.upstream.frames) {
    if (f.kind == Kind::Hello) hello = f;
    r.master.receive(f, r.now);
  }
  assert(hello.epoch != oldCommand.epoch);
  rebooted.receive(oldCommand, r.now); assert(!r.motors.state.motors[0].on);
  const uint32_t revision = r.events.state.revision;
  hello.payload[4] = 1; hello.payload[5] = 100;
  r.master.receive(hello, r.now);  // The already consumed probe cannot update state again.
  assert(r.events.state.revision == revision); assert(!r.events.state.motors[0].on);
}

static void unknownEpochStopDeadline() {
  Rig r;
  r.master.stop(77, r.now);
  r.dropUp = true; r.run(460);
  assert(r.events.results.back() == std::make_pair(uint32_t(77), false));
}

int main() {
  codec(); motorParser(); normalAndDuplicates(); stopBarrier(); timeoutAndEpoch();
  oneWayAndBrokerLoss(); queueBudgetAndLostAck(); rebootAndWrongPeer(); clockRollover();
  slaveRestartAndStaleReplies(); unknownEpochStopDeadline();
  puts("PASS: codec, retries, STOP barrier, lease expiry, one-way loss, broker loss, queue budget, reboot, rollover");
}
