#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Arduino.h>

// Global hardware state
bool hardwareOff = false;

// Motor state tracking
MotorState motor1State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};
MotorState motor2State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};

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
  int pwmValue = map(speed, 0, 100, 0, 255);
  pwmValue = constrain(pwmValue, 0, 255);

  if (motorNum == 1) {
    if (speed == 0) {
      ledcWrite(MOTOR1_LEFT_PIN, 0);
      ledcWrite(MOTOR1_RIGHT_PIN, 0);
    } else if (direction == 'L') {
      ledcWrite(MOTOR1_LEFT_PIN, pwmValue);
      ledcWrite(MOTOR1_RIGHT_PIN, 0);
    } else if (direction == 'R') {
      ledcWrite(MOTOR1_LEFT_PIN, 0);
      ledcWrite(MOTOR1_RIGHT_PIN, pwmValue);
    }
  } else if (motorNum == 2) {
    if (speed == 0) {
      ledcWrite(MOTOR2_LEFT_PIN, 0);
      ledcWrite(MOTOR2_RIGHT_PIN, 0);
    } else if (direction == 'L') {
      ledcWrite(MOTOR2_LEFT_PIN, pwmValue);
      ledcWrite(MOTOR2_RIGHT_PIN, 0);
    } else if (direction == 'R') {
      ledcWrite(MOTOR2_LEFT_PIN, 0);
      ledcWrite(MOTOR2_RIGHT_PIN, pwmValue);
    }
  }
}

// Function: Smooth motor update with custom ramp and direction change support
void updateMotorSmoothly() {
  unsigned long currentTime = millis();

  // ----- MOTOR 1 LOGIKA -----
  if (currentTime - motor1State.lastUpdate >= SMOOTH_DELAY) {
    
    // 1. LOGIKA ZMENY SMERU (Čaká na nulovú rýchlosť)
    if (motor1State.pendingDirectionChange) {
       if (motor1State.currentSpeed == 0) {
          motor1State.direction = motor1State.newDirection;
          motor1State.targetSpeed = motor1State.savedSpeed;
          motor1State.pendingDirectionChange = false;
          debugPrint("Motor1 reached 0, flipping direction to: " + String(motor1State.direction) + ", resuming to: " + String(motor1State.targetSpeed));
       } 
       else {
          motor1State.targetSpeed = 0;
          motor1State.rampActive = false; // Pri otáčaní nepoužívame custom rampu, ale štandardný dobeh
       }
    }

    // 2. LOGIKA CUSTOM RAMPY (Iba ak nemeníme smer)
    if (motor1State.rampActive && !motor1State.pendingDirectionChange) {
      if (currentTime >= motor1State.rampStartTime + motor1State.rampDurationMs) {
        motor1State.currentSpeed = motor1State.targetSpeed;
        motor1State.rampActive = false;
        debugPrint("Motor1 Ramp finished.");
      } else {
        unsigned long elapsedTime = currentTime - motor1State.rampStartTime;
        long deltaSpeed = motor1State.targetSpeed - motor1State.rampStartSpeed;
        motor1State.currentSpeed = motor1State.rampStartSpeed + (int)((deltaSpeed * elapsedTime) / motor1State.rampDurationMs);
        updateMotorPWM(1, motor1State.currentSpeed, motor1State.direction);
        motor1State.lastUpdate = currentTime;
        return; // Pri rampe neriešime štandardný krok nižšie
      }
    }
    
    // 3. ŠTANDARDNÁ Plynulá zmena rýchlosti
    if (motor1State.currentSpeed != motor1State.targetSpeed) {
      if (motor1State.currentSpeed < motor1State.targetSpeed) {
        motor1State.currentSpeed = min(motor1State.currentSpeed + SMOOTH_STEP, motor1State.targetSpeed);
      } else {
        motor1State.currentSpeed = max(motor1State.currentSpeed - SMOOTH_STEP, motor1State.targetSpeed);
      }
      updateMotorPWM(1, motor1State.currentSpeed, motor1State.direction);
      motor1State.lastUpdate = currentTime;
    }
  }

  // ----- MOTOR 2 LOGIKA -----
  if (currentTime - motor2State.lastUpdate >= SMOOTH_DELAY) {

    // 1. LOGIKA ZMENY SMERU
    if (motor2State.pendingDirectionChange) {
       if (motor2State.currentSpeed == 0) {
          motor2State.direction = motor2State.newDirection;
          motor2State.targetSpeed = motor2State.savedSpeed;
          motor2State.pendingDirectionChange = false;
          debugPrint("Motor2 reached 0, flipping direction to: " + String(motor2State.direction));
       } else {
          motor2State.targetSpeed = 0;
          motor2State.rampActive = false;
       }
    }

    // 2. LOGIKA CUSTOM RAMPY
    if (motor2State.rampActive && !motor2State.pendingDirectionChange) {
      if (currentTime >= motor2State.rampStartTime + motor2State.rampDurationMs) {
        motor2State.currentSpeed = motor2State.targetSpeed;
        motor2State.rampActive = false;
        debugPrint("Motor2 Ramp finished.");
      } else {
        unsigned long elapsedTime = currentTime - motor2State.rampStartTime;
        long deltaSpeed = motor2State.targetSpeed - motor2State.rampStartSpeed;
        motor2State.currentSpeed = motor2State.rampStartSpeed + (int)((deltaSpeed * elapsedTime) / motor2State.rampDurationMs);
        updateMotorPWM(2, motor2State.currentSpeed, motor2State.direction);
        motor2State.lastUpdate = currentTime;
        return; 
      }
    }
    
    // 3. ŠTANDARDNÁ Plynulá zmena
    if (motor2State.currentSpeed != motor2State.targetSpeed) {
      if (motor2State.currentSpeed < motor2State.targetSpeed) {
        motor2State.currentSpeed = min(motor2State.currentSpeed + SMOOTH_STEP, motor2State.targetSpeed);
      } else {
        motor2State.currentSpeed = max(motor2State.currentSpeed - SMOOTH_STEP, motor2State.targetSpeed);
      }
      updateMotorPWM(2, motor2State.currentSpeed, motor2State.direction);
      motor2State.lastUpdate = currentTime;
    }
  }
}

// controlMotor1
void controlMotor1(const char* command, const char* speed, const char* direction, const char* rampTime) {
  debugPrint("Motor1 CMD: " + String(command) + " Spd:" + String(speed) + " Dir:" + String(direction));

  if (strcmp(command, "ON") == 0) {
    motor1State.enabled = true;
    digitalWrite(MOTOR1_ENABLE_PIN, HIGH);
    
    int targetSpd = atoi(speed);
    char targetDir = direction[0];
    unsigned long rampDuration = atol(rampTime);

    // --- FIX: Detekcia zmeny smeru za behu ---
    if (motor1State.currentSpeed > 0 && motor1State.direction != targetDir) {
        debugPrint("Motor1 changing direction while running! Initiating smooth reversal.");
        motor1State.pendingDirectionChange = true;
        motor1State.newDirection = targetDir;
        motor1State.savedSpeed = targetSpd;
        motor1State.targetSpeed = 0;
        motor1State.rampActive = false; // Vypneme rampu pre spomalenie
        hardwareOff = false;
        return; // DÔLEŽITÉ: Nespustiť kód nižšie, kým sa motor neotočí
    }
    // -----------------------------------------
    
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
    // --- FIX: PLYNULÉ ZASTAVENIE ---
    if (motor1State.enabled) {
        motor1State.targetSpeed = 0;
        motor1State.speed = 0;
        motor1State.rampActive = false; // Použije sa štandardný SMOOTH_STEP
        debugPrint("Motor1 stopping smoothly (OFF command)");
        // Nechávame enabled = true, kým nedobehne, resp. kým sa nezavolá turnOffHardware
    }

  } else if (strcmp(command, "SPEED") == 0) {
    if (motor1State.enabled) {
      motor1State.speed = atoi(speed);
      motor1State.targetSpeed = motor1State.speed;
      motor1State.rampActive = false;
    }

  } else if (strcmp(command, "DIR") == 0) {
    if (motor1State.enabled) {
      char newDir = direction[0];
      if (motor1State.direction == newDir) return;

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
    }
  }
}

// controlMotor2
void controlMotor2(const char* command, const char* speed, const char* direction, const char* rampTime) {
  debugPrint("Motor2 CMD: " + String(command) + " Spd:" + String(speed) + " Dir:" + String(direction));

  if (strcmp(command, "ON") == 0) {
    motor2State.enabled = true;
    digitalWrite(MOTOR2_ENABLE_PIN, HIGH);
    
    int targetSpd = atoi(speed);
    char targetDir = direction[0];
    unsigned long rampDuration = atol(rampTime);

    // --- FIX: Detekcia zmeny smeru za behu ---
    if (motor2State.currentSpeed > 0 && motor2State.direction != targetDir) {
        debugPrint("Motor2 changing direction while running! Initiating smooth reversal.");
        motor2State.pendingDirectionChange = true;
        motor2State.newDirection = targetDir;
        motor2State.savedSpeed = targetSpd;
        motor2State.targetSpeed = 0;
        motor2State.rampActive = false;
        hardwareOff = false;
        return; 
    }
    // -----------------------------------------

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
    // --- FIX: PLYNULÉ ZASTAVENIE ---
    if (motor2State.enabled) {
        motor2State.targetSpeed = 0;
        motor2State.speed = 0;
        motor2State.rampActive = false;
        debugPrint("Motor2 stopping smoothly (OFF command)");
    }

  } else if (strcmp(command, "SPEED") == 0) {
    if (motor2State.enabled) {
      motor2State.speed = atoi(speed);
      motor2State.targetSpeed = motor2State.speed;
      motor2State.rampActive = false;
    }

  } else if (strcmp(command, "DIR") == 0) {
    if (motor2State.enabled) {
      char newDir = direction[0];
      if (motor2State.direction == newDir) return;

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
    }
  }
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

  debugPrint("All motors turned OFF (Hard Reset)");
  hardwareOff = true;
}