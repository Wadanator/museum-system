#include "motor_commands.h"
#include "hardware.h"
#include "config.h"
#include <MuseumMotorCommand.h>

unsigned long lastCommandTime = 0;

bool executeMotorCommand(museum::Target target, const char* command) {
  if (!command) return false;
  if (target == museum::Target::All) {
    if (strcmp(command, "STOP")) return false;
    turnOffHardware(); lastCommandTime = millis(); return true;
  }
  if (target != museum::Target::Motor1 && target != museum::Target::Motor2) return false;
  museum::MotorCommand parsed;
  if (!museum::parseMotorCommand(command, NO_COMMAND_TIMEOUT, parsed)) return false;
  const bool ok = target == museum::Target::Motor1
      ? controlMotor1(parsed.action, parsed.speed, parsed.direction, parsed.ramp)
      : controlMotor2(parsed.action, parsed.speed, parsed.direction, parsed.ramp);
  if (ok) lastCommandTime = millis();
  return ok;
}

museum::Snapshot readMotorSnapshot() {
  museum::Snapshot snapshot;
  const MotorState* motors[] = {&motor1State, &motor2State};
  for (size_t i = 0; i < 2; ++i) {
    const MotorState& state = *motors[i];
    const bool pending = state.pendingDirectionChange && state.savedSpeed > 0;
    auto& m = snapshot.motors[i];
    m.on = state.enabled && (state.speed > 0 || state.targetSpeed > 0 || pending);
    m.speed = m.on ? constrain(pending ? state.savedSpeed : max(state.speed, state.targetSpeed), 0, 100) : 0;
    m.direction = state.pendingDirectionChange ? state.newDirection : state.direction;
  }
  return snapshot;
}
