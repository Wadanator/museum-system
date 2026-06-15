#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Arduino.h>

// Motor driver output state.
bool hardwareOff = false;

// Runtime state for each motor.
MotorState motor1State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};
MotorState motor2State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};

void updateMotorPWM(int motorNum, int speed, char direction);

static int signedPwmFromState(const MotorState& state) {
  int safeSpeed = constrain(state.currentSpeed, 0, 100);
  int pwmValue = map(safeSpeed, 0, 100, 0, 255);
  pwmValue = constrain(pwmValue, 0, 255);

  if (safeSpeed == 0 || state.direction == 'S') {
    return 0;
  }

  return (state.direction == 'L') ? -pwmValue : pwmValue;
}

static int signedTargetPwmFromState(const MotorState& state) {
  int safeSpeed = constrain(state.targetSpeed, 0, 100);
  int pwmValue = map(safeSpeed, 0, 100, 0, 255);
  pwmValue = constrain(pwmValue, 0, 255);

  if (safeSpeed == 0 || state.direction == 'S') {
    return 0;
  }

  return (state.direction == 'L') ? -pwmValue : pwmValue;
}

static void printPwmTelemetry(unsigned long currentTime) {
  if (!PWM_TELEMETRY) return;

  static unsigned long lastTelemetryTime = 0;
  if (currentTime - lastTelemetryTime < PWM_TELEMETRY_INTERVAL) return;
  lastTelemetryTime = currentTime;

  Serial.print("M1_PWM:");
  Serial.print(signedPwmFromState(motor1State));
  Serial.print("\tM1_TARGET:");
  Serial.print(signedTargetPwmFromState(motor1State));
  Serial.print("\tM2_PWM:");
  Serial.print(signedPwmFromState(motor2State));
  Serial.print("\tM2_TARGET:");
  Serial.println(signedTargetPwmFromState(motor2State));
}

static bool parseSpeed(const char* speed, int& value) {
  if (speed == nullptr || speed[0] == '\0') return false;

  char* endPtr = nullptr;
  long parsed = strtol(speed, &endPtr, 10);
  if (endPtr == speed || *endPtr != '\0') return false;

  value = constrain((int)parsed, 0, 100);
  return true;
}

static char normalizedDirection(const char* direction) {
  if (direction == nullptr || direction[0] == '\0') return 'S';
  char value = direction[0];
  if (value == 'l') value = 'L';
  if (value == 'r') value = 'R';
  if (value == 'L' || value == 'R') return value;
  return 'S';
}

static void setMotorEnabled(int motorNum, bool enabled) {
  int pin = (motorNum == 1) ? MOTOR1_ENABLE_PIN : MOTOR2_ENABLE_PIN;
  digitalWrite(pin, enabled ? HIGH : LOW);
}

static void markMotorStopped(int motorNum, MotorState& state) {
  if (!state.enabled) return;
  if (state.currentSpeed != 0 || state.targetSpeed != 0 || state.speed != 0) return;
  if (state.pendingDirectionChange || state.rampActive) return;

  updateMotorPWM(motorNum, 0, 'S');
  setMotorEnabled(motorNum, false);
  state.enabled = false;
  state.direction = 'S';
  state.newDirection = 'S';
  state.savedSpeed = 0;
  state.lastUpdate = millis();
  debugPrint("Motor" + String(motorNum) + " disabled after controlled stop");

  if (!motor1State.enabled && !motor2State.enabled) {
    hardwareOff = true;
  }
}

void initializeHardware() {
  debugPrint("Initializing PWM motors...");

  ledcAttach(MOTOR1_LEFT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcAttach(MOTOR1_RIGHT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);

  ledcAttach(MOTOR2_LEFT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcAttach(MOTOR2_RIGHT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);

  pinMode(MOTOR1_ENABLE_PIN, OUTPUT);
  pinMode(MOTOR2_ENABLE_PIN, OUTPUT);

  turnOffHardware();
  debugPrint("Hardware initialized - PWM motors ready");
}

void updateMotorPWM(int motorNum, int speed, char direction) {
  int safeSpeed = constrain(speed, 0, 100);
  int pwmValue = map(safeSpeed, 0, 100, 0, 255);
  pwmValue = constrain(pwmValue, 0, 255);

  if (motorNum == 1) {
    if (safeSpeed == 0) {
      ledcWrite(MOTOR1_LEFT_PIN, 0);
      ledcWrite(MOTOR1_RIGHT_PIN, 0);
    } else if (direction == 'L') {
      ledcWrite(MOTOR1_LEFT_PIN, pwmValue);
      ledcWrite(MOTOR1_RIGHT_PIN, 0);
    } else if (direction == 'R') {
      ledcWrite(MOTOR1_LEFT_PIN, 0);
      ledcWrite(MOTOR1_RIGHT_PIN, pwmValue);
    } else {
      ledcWrite(MOTOR1_LEFT_PIN, 0);
      ledcWrite(MOTOR1_RIGHT_PIN, 0);
    }
  } else if (motorNum == 2) {
    if (safeSpeed == 0) {
      ledcWrite(MOTOR2_LEFT_PIN, 0);
      ledcWrite(MOTOR2_RIGHT_PIN, 0);
    } else if (direction == 'L') {
      ledcWrite(MOTOR2_LEFT_PIN, pwmValue);
      ledcWrite(MOTOR2_RIGHT_PIN, 0);
    } else if (direction == 'R') {
      ledcWrite(MOTOR2_LEFT_PIN, 0);
      ledcWrite(MOTOR2_RIGHT_PIN, pwmValue);
    } else {
      ledcWrite(MOTOR2_LEFT_PIN, 0);
      ledcWrite(MOTOR2_RIGHT_PIN, 0);
    }
  }
}

void updateMotorSmoothly() {
  unsigned long currentTime = millis();

  // -------------------- MOTOR 1 --------------------
  if (currentTime - motor1State.lastUpdate >= SMOOTH_DELAY) {
    bool rampStepHandled = false;

    // Direction reversal is staged through zero speed.
    if (motor1State.pendingDirectionChange) {
      if (motor1State.currentSpeed == 0) {
        motor1State.direction = motor1State.newDirection;
        motor1State.targetSpeed = motor1State.savedSpeed;
        motor1State.pendingDirectionChange = false;

        debugPrint(
          "Motor1 reached 0, flipping direction to: " +
          String(motor1State.direction) +
          ", resuming to: " +
          String(motor1State.targetSpeed)
        );
      } else {
        motor1State.targetSpeed = 0;
        motor1State.rampActive = false;
      }
    }

    // Command-defined ramp.
    if (motor1State.rampActive &&
        !motor1State.pendingDirectionChange) {

      if (currentTime >=
          motor1State.rampStartTime +
          motor1State.rampDurationMs) {

        motor1State.currentSpeed =
          motor1State.targetSpeed;

        motor1State.rampActive = false;

        updateMotorPWM(
          1,
          motor1State.currentSpeed,
          motor1State.direction
        );

        motor1State.lastUpdate = currentTime;
        rampStepHandled = true;

        debugPrint("Motor1 Ramp finished.");
      } else {
        unsigned long elapsedTime =
          currentTime - motor1State.rampStartTime;

        long deltaSpeed =
          motor1State.targetSpeed -
          motor1State.rampStartSpeed;

        motor1State.currentSpeed =
          motor1State.rampStartSpeed +
          (int)(
            (deltaSpeed * elapsedTime) /
            motor1State.rampDurationMs
          );

        updateMotorPWM(
          1,
          motor1State.currentSpeed,
          motor1State.direction
        );

        motor1State.lastUpdate = currentTime;
        rampStepHandled = true;
      }
    }

    // Normal smooth stepping.
    if (!rampStepHandled &&
        motor1State.currentSpeed !=
        motor1State.targetSpeed) {

      if (motor1State.currentSpeed <
          motor1State.targetSpeed) {

        motor1State.currentSpeed = min(
          motor1State.currentSpeed + SMOOTH_STEP,
          motor1State.targetSpeed
        );
      } else {
        motor1State.currentSpeed = max(
          motor1State.currentSpeed - SMOOTH_STEP,
          motor1State.targetSpeed
        );
      }

      updateMotorPWM(
        1,
        motor1State.currentSpeed,
        motor1State.direction
      );

      motor1State.lastUpdate = currentTime;
    }

    markMotorStopped(1, motor1State);
  }

  // -------------------- MOTOR 2 --------------------
  if (currentTime - motor2State.lastUpdate >= SMOOTH_DELAY) {
    bool rampStepHandled = false;

    // Direction reversal is staged through zero speed.
    if (motor2State.pendingDirectionChange) {
      if (motor2State.currentSpeed == 0) {
        motor2State.direction = motor2State.newDirection;
        motor2State.targetSpeed = motor2State.savedSpeed;
        motor2State.pendingDirectionChange = false;

        debugPrint(
          "Motor2 reached 0, flipping direction to: " +
          String(motor2State.direction) +
          ", resuming to: " +
          String(motor2State.targetSpeed)
        );
      } else {
        motor2State.targetSpeed = 0;
        motor2State.rampActive = false;
      }
    }

    // Command-defined ramp.
    if (motor2State.rampActive &&
        !motor2State.pendingDirectionChange) {

      if (currentTime >=
          motor2State.rampStartTime +
          motor2State.rampDurationMs) {

        motor2State.currentSpeed =
          motor2State.targetSpeed;

        motor2State.rampActive = false;

        updateMotorPWM(
          2,
          motor2State.currentSpeed,
          motor2State.direction
        );

        motor2State.lastUpdate = currentTime;
        rampStepHandled = true;

        debugPrint("Motor2 Ramp finished.");
      } else {
        unsigned long elapsedTime =
          currentTime - motor2State.rampStartTime;

        long deltaSpeed =
          motor2State.targetSpeed -
          motor2State.rampStartSpeed;

        motor2State.currentSpeed =
          motor2State.rampStartSpeed +
          (int)(
            (deltaSpeed * elapsedTime) /
            motor2State.rampDurationMs
          );

        updateMotorPWM(
          2,
          motor2State.currentSpeed,
          motor2State.direction
        );

        motor2State.lastUpdate = currentTime;
        rampStepHandled = true;
      }
    }

    // Normal smooth stepping.
    if (!rampStepHandled &&
        motor2State.currentSpeed !=
        motor2State.targetSpeed) {

      if (motor2State.currentSpeed <
          motor2State.targetSpeed) {

        motor2State.currentSpeed = min(
          motor2State.currentSpeed + SMOOTH_STEP,
          motor2State.targetSpeed
        );
      } else {
        motor2State.currentSpeed = max(
          motor2State.currentSpeed - SMOOTH_STEP,
          motor2State.targetSpeed
        );
      }

      updateMotorPWM(
        2,
        motor2State.currentSpeed,
        motor2State.direction
      );

      motor2State.lastUpdate = currentTime;
    }

    markMotorStopped(2, motor2State);
  }

  // Print exactly once per telemetry interval.
  printPwmTelemetry(currentTime);
}


bool controlMotor1(const char* command, const char* speed, const char* direction, const char* rampTime) {
  debugPrint("Motor1 CMD: " + String(command) + " Spd:" + String(speed) + " Dir:" + String(direction));

  if (strcmp(command, "ON") == 0) {
    int targetSpd = 0;
    if (!parseSpeed(speed, targetSpd)) {
      debugPrint("Motor1 rejected ON command with invalid speed");
      return false;
    }

    char targetDir = normalizedDirection(direction);
    if (targetSpd <= 0 || targetDir == 'S') {
      debugPrint("Motor1 rejected ON command with invalid speed or direction");
      return false;
    }

    motor1State.enabled = true;
    setMotorEnabled(1, true);

    unsigned long rampDuration = atol(rampTime);

    // A running motor must decelerate to zero before reversing direction.
    if (motor1State.currentSpeed > 0 && motor1State.direction != targetDir) {
        debugPrint("Motor1 changing direction while running. Initiating smooth reversal.");
        motor1State.pendingDirectionChange = true;
        motor1State.newDirection = targetDir;
        motor1State.savedSpeed = targetSpd;
        motor1State.speed = targetSpd;
        motor1State.targetSpeed = 0;
        motor1State.rampActive = false;
        hardwareOff = false;
        return true;
    }
    
    motor1State.direction = targetDir;
    motor1State.speed = targetSpd;
    motor1State.pendingDirectionChange = false;

    if (rampDuration > 0) {
      motor1State.rampActive = true;
      motor1State.rampDurationMs = rampDuration;
      motor1State.rampStartTime = millis();
      motor1State.rampStartSpeed = motor1State.currentSpeed;
      motor1State.targetSpeed = motor1State.speed;
    } else {
      motor1State.targetSpeed = motor1State.speed;
      motor1State.rampActive = false;
    }
    
    hardwareOff = false;

  } else if (strcmp(command, "OFF") == 0) {
    // OFF requests a controlled stop through the smooth updater.
    if (motor1State.enabled) {
        motor1State.targetSpeed = 0;
        motor1State.speed = 0;
        motor1State.rampActive = false;
        motor1State.pendingDirectionChange = false;
        motor1State.savedSpeed = 0;
        motor1State.newDirection = 'S';
        debugPrint("Motor1 stopping smoothly (OFF command)");
    } else {
        markMotorStopped(1, motor1State);
    }

  } else if (strcmp(command, "SPEED") == 0) {
    if (motor1State.enabled) {
      int targetSpd = 0;
      if (!parseSpeed(speed, targetSpd)) {
        debugPrint("Motor1 rejected SPEED command with invalid speed");
        return false;
      }

      motor1State.speed = targetSpd;
      motor1State.targetSpeed = motor1State.speed;
      motor1State.rampActive = false;
      if (motor1State.speed == 0) {
        motor1State.pendingDirectionChange = false;
        motor1State.savedSpeed = 0;
        motor1State.newDirection = 'S';
      }
    } else {
      return false;
    }

  } else if (strcmp(command, "DIR") == 0) {
    if (motor1State.enabled) {
      char newDir = normalizedDirection(direction);
      if (newDir == 'S') return false;
      if (motor1State.direction == newDir) return true;

      if (motor1State.currentSpeed > 0) {
        motor1State.savedSpeed = motor1State.speed;
        motor1State.newDirection = newDir;
        motor1State.pendingDirectionChange = true;
        motor1State.targetSpeed = 0;
        motor1State.rampActive = false;
        debugPrint("Motor1 reversing direction via DIR command");
      } else {
        motor1State.direction = newDir;
      }
    } else {
      return false;
    }
  } else {
    return false;
  }
  return true;
}

bool controlMotor2(const char* command, const char* speed, const char* direction, const char* rampTime) {
  debugPrint("Motor2 CMD: " + String(command) + " Spd:" + String(speed) + " Dir:" + String(direction));

  if (strcmp(command, "ON") == 0) {
    int targetSpd = 0;
    if (!parseSpeed(speed, targetSpd)) {
      debugPrint("Motor2 rejected ON command with invalid speed");
      return false;
    }

    char targetDir = normalizedDirection(direction);
    if (targetSpd <= 0 || targetDir == 'S') {
      debugPrint("Motor2 rejected ON command with invalid speed or direction");
      return false;
    }

    motor2State.enabled = true;
    setMotorEnabled(2, true);

    unsigned long rampDuration = atol(rampTime);

    // A running motor must decelerate to zero before reversing direction.
    if (motor2State.currentSpeed > 0 && motor2State.direction != targetDir) {
        debugPrint("Motor2 changing direction while running. Initiating smooth reversal.");
        motor2State.pendingDirectionChange = true;
        motor2State.newDirection = targetDir;
        motor2State.savedSpeed = targetSpd;
        motor2State.speed = targetSpd;
        motor2State.targetSpeed = 0;
        motor2State.rampActive = false;
        hardwareOff = false;
        return true;
    }

    motor2State.direction = targetDir;
    motor2State.speed = targetSpd;
    motor2State.pendingDirectionChange = false;

    if (rampDuration > 0) {
      motor2State.rampActive = true;
      motor2State.rampDurationMs = rampDuration;
      motor2State.rampStartTime = millis();
      motor2State.rampStartSpeed = motor2State.currentSpeed;
      motor2State.targetSpeed = motor2State.speed;
    } else {
      motor2State.targetSpeed = motor2State.speed;
      motor2State.rampActive = false;
    }
    
    hardwareOff = false;

  } else if (strcmp(command, "OFF") == 0) {
    // OFF requests a controlled stop through the smooth updater.
    if (motor2State.enabled) {
        motor2State.targetSpeed = 0;
        motor2State.speed = 0;
        motor2State.rampActive = false;
        motor2State.pendingDirectionChange = false;
        motor2State.savedSpeed = 0;
        motor2State.newDirection = 'S';
        debugPrint("Motor2 stopping smoothly (OFF command)");
    } else {
        markMotorStopped(2, motor2State);
    }

  } else if (strcmp(command, "SPEED") == 0) {
    if (motor2State.enabled) {
      int targetSpd = 0;
      if (!parseSpeed(speed, targetSpd)) {
        debugPrint("Motor2 rejected SPEED command with invalid speed");
        return false;
      }

      motor2State.speed = targetSpd;
      motor2State.targetSpeed = motor2State.speed;
      motor2State.rampActive = false;
      if (motor2State.speed == 0) {
        motor2State.pendingDirectionChange = false;
        motor2State.savedSpeed = 0;
        motor2State.newDirection = 'S';
      }
    } else {
      return false;
    }

  } else if (strcmp(command, "DIR") == 0) {
    if (motor2State.enabled) {
      char newDir = normalizedDirection(direction);
      if (newDir == 'S') return false;
      if (motor2State.direction == newDir) return true;

      if (motor2State.currentSpeed > 0) {
        motor2State.savedSpeed = motor2State.speed;
        motor2State.newDirection = newDir;
        motor2State.pendingDirectionChange = true;
        motor2State.targetSpeed = 0;
        motor2State.rampActive = false;
        debugPrint("Motor2 reversing direction via DIR command");
      } else {
        motor2State.direction = newDir;
      }
    } else {
      return false;
    }
  } else {
    return false;
  }
  return true;
}

void turnOffHardware() {
  digitalWrite(MOTOR1_ENABLE_PIN, LOW);
  digitalWrite(MOTOR2_ENABLE_PIN, LOW);
  ledcWrite(MOTOR1_LEFT_PIN, 0);
  ledcWrite(MOTOR1_RIGHT_PIN, 0);
  ledcWrite(MOTOR2_LEFT_PIN, 0);
  ledcWrite(MOTOR2_RIGHT_PIN, 0);

  motor1State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};
  motor2State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};

  debugPrint("All motors turned OFF (hard reset)");
  hardwareOff = true;
}
