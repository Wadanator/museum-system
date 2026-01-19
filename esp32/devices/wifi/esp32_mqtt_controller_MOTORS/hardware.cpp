#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Arduino.h>

// Global hardware state
bool hardwareOff = false;

// Motor state tracking - expanded for smooth control
// Inicializácia s pridanými 4 poliami pre rampu (false, 0, 0, 0)
MotorState motor1State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};
MotorState motor2State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};

void initializeHardware() {
  // Setup PWM for motors using new ESP32 Arduino Core API
  debugPrint("Initializing PWM motors...");

  // Motor 1 PWM setup
  ledcAttach(MOTOR1_LEFT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcAttach(MOTOR1_RIGHT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);

  // Motor 2 PWM setup
  ledcAttach(MOTOR2_LEFT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcAttach(MOTOR2_RIGHT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);

  // Enable pins setup
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
    
    // 1. LOGIKA CUSTOM RAMPY (Time-based acceleration/deceleration)
    if (motor1State.rampActive) {
      if (currentTime >= motor1State.rampStartTime + motor1State.rampDurationMs) {
        // Rampa skončila, stabilizujeme rýchlosť a vypneme rampu
        motor1State.currentSpeed = motor1State.targetSpeed;
        motor1State.rampActive = false;
        debugPrint("Motor1 Ramp finished. Speed stabilized at: " + String(motor1State.targetSpeed) + "%");
      } else {
        // Vypočítame aktuálne požadovanú rýchlosť na rampe (Time-based interpolation)
        unsigned long elapsedTime = currentTime - motor1State.rampStartTime;
        long deltaSpeed = motor1State.targetSpeed - motor1State.rampStartSpeed;
        
        // Nová rýchlosť (pomocou celočíselnej matematiky)
        // Toto zabezpečuje plynulú zmenu počas celého rampDurationMs
        motor1State.currentSpeed = motor1State.rampStartSpeed + (int)((deltaSpeed * elapsedTime) / motor1State.rampDurationMs);

        // Aplikujeme vypočítanú rýchlosť
        updateMotorPWM(1, motor1State.currentSpeed, motor1State.direction);
        motor1State.lastUpdate = currentTime;
        return; // Preskočíme štandardnú smooth logiku
      }
    }
    
    // 2. LOGIKA ZMENY SMERU (iba ak Rampa nie je aktívna)
    if (motor1State.pendingDirectionChange && motor1State.currentSpeed == 0) {
      // The motor has stopped, now change direction and resume
      motor1State.direction = motor1State.newDirection;
      motor1State.targetSpeed = motor1State.savedSpeed;
      motor1State.pendingDirectionChange = false;
      debugPrint("Motor1 direction changed to: " + String(motor1State.direction) + ", resuming speed: " + String(motor1State.targetSpeed));
    }

    // 3. ŠTANDARDNÁ Plynulá zmena rýchlosti (SMOOTH_STEP/DELAY)
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

  // ----- MOTOR 2 LOGIKA (rovnaké zmeny) -----
  if (currentTime - motor2State.lastUpdate >= SMOOTH_DELAY) {

    // 1. LOGIKA CUSTOM RAMPY
    if (motor2State.rampActive) {
      if (currentTime >= motor2State.rampStartTime + motor2State.rampDurationMs) {
        motor2State.currentSpeed = motor2State.targetSpeed;
        motor2State.rampActive = false;
        debugPrint("Motor2 Ramp finished. Speed stabilized at: " + String(motor2State.targetSpeed) + "%");
      } else {
        unsigned long elapsedTime = currentTime - motor2State.rampStartTime;
        long deltaSpeed = motor2State.targetSpeed - motor2State.rampStartSpeed;
        
        motor2State.currentSpeed = motor2State.rampStartSpeed + (int)((deltaSpeed * elapsedTime) / motor2State.rampDurationMs);

        updateMotorPWM(2, motor2State.currentSpeed, motor2State.direction);
        motor2State.lastUpdate = currentTime;
        return; 
      }
    }
    
    // 2. LOGIKA ZMENY SMERU
    if (motor2State.pendingDirectionChange && motor2State.currentSpeed == 0) {
      motor2State.direction = motor2State.newDirection;
      motor2State.targetSpeed = motor2State.savedSpeed;
      motor2State.pendingDirectionChange = false;
      debugPrint("Motor2 direction changed to: " + String(motor2State.direction) + ", resuming speed: " + String(motor2State.targetSpeed));
    }

    // 3. ŠTANDARDNÁ Plynulá zmena rýchlosti
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

// controlMotor1 (s novým rampTime parametrom)
void controlMotor1(const char* command, const char* speed, const char* direction, const char* rampTime) {
  debugPrint("Motor1 command: " + String(command) + ", speed: " + String(speed) + ", dir: " + String(direction) + ", rampTime: " + String(rampTime));

  if (strcmp(command, "ON") == 0) {
    motor1State.enabled = true;
    motor1State.speed = atoi(speed);
    motor1State.direction = direction[0];
    motor1State.pendingDirectionChange = false;
    digitalWrite(MOTOR1_ENABLE_PIN, HIGH);
    
    unsigned long rampDuration = atol(rampTime); // Konverzia na unsigned long (ms)
    
    if (rampDuration > 0) {
      // CUSTOM RAMPA AKTÍVNA
      motor1State.rampActive = true;
      motor1State.rampDurationMs = rampDuration;
      motor1State.rampStartTime = millis();
      motor1State.rampStartSpeed = motor1State.currentSpeed; // Začíname z aktuálnej rýchlosti
      motor1State.targetSpeed = motor1State.speed;           // Cieľová rýchlosť
      debugPrint("Motor1 ON - CUSTOM RAMP Target Speed: " + String(motor1State.speed) + "%, Duration: " + String(rampDuration) + "ms");
    } else {
      // POUŽIJE SA ŠTANDARDNÝ SMOOTH PRECHOD
      motor1State.targetSpeed = motor1State.speed;
      motor1State.rampActive = false;
      debugPrint("Motor1 ON - STANDARD SMOOTH Target Speed: " + String(motor1State.speed) + "%, Dir: " + String(motor1State.direction));
    }
    
    hardwareOff = false;

  } else if (strcmp(command, "OFF") == 0) {
    motor1State.enabled = false;
    motor1State.speed = 0;
    motor1State.targetSpeed = 0;
    motor1State.pendingDirectionChange = false;
    motor1State.rampActive = false; // Zrušenie custom rampy
    debugPrint("Motor1 OFF - smooth stopping...");

  } else if (strcmp(command, "SPEED") == 0) {
    if (motor1State.enabled) {
      motor1State.speed = atoi(speed);
      motor1State.targetSpeed = motor1State.speed;
      motor1State.rampActive = false; // Rýchlosť sa mení štandardne (zruší custom ramp)
      debugPrint("Motor1 speed target set to: " + String(motor1State.speed) + "%");
    } else {
      debugPrint("Motor1 not enabled, ignoring speed command");
    }

  } else if (strcmp(command, "DIR") == 0) {
    if (motor1State.enabled) {
      motor1State.rampActive = false; // Zruší custom ramp
      char newDir = direction[0];

      if (motor1State.direction == newDir) {
        debugPrint("Motor1 already running in direction: " + String(newDir));
        return;
      }

      if (motor1State.currentSpeed > 0) {
        motor1State.savedSpeed = motor1State.speed;
        motor1State.newDirection = newDir;
        motor1State.pendingDirectionChange = true;
        motor1State.targetSpeed = 0;
        debugPrint("Motor1 stopping for direction change from " + String(motor1State.direction) + " to " + String(newDir));
      } else {
        motor1State.direction = newDir;
        debugPrint("Motor1 direction changed to: " + String(newDir) + " (motor was stopped)");
      }
    } else {
      debugPrint("Motor1 not enabled, ignoring direction command");
    }

  } else {
    debugPrint("Unknown motor1 command: " + String(command));
  }
}

// controlMotor2 (s novým rampTime parametrom)
void controlMotor2(const char* command, const char* speed, const char* direction, const char* rampTime) {
  debugPrint("Motor2 command: " + String(command) + ", speed: " + String(speed) + ", dir: " + String(direction) + ", rampTime: " + String(rampTime));

  if (strcmp(command, "ON") == 0) {
    motor2State.enabled = true;
    motor2State.speed = atoi(speed);
    motor2State.direction = direction[0];
    motor2State.pendingDirectionChange = false;
    digitalWrite(MOTOR2_ENABLE_PIN, HIGH);
    
    unsigned long rampDuration = atol(rampTime); 
    
    if (rampDuration > 0) {
      motor2State.rampActive = true;
      motor2State.rampDurationMs = rampDuration;
      motor2State.rampStartTime = millis();
      motor2State.rampStartSpeed = motor2State.currentSpeed;
      motor2State.targetSpeed = motor2State.speed;
      debugPrint("Motor2 ON - CUSTOM RAMP Target Speed: " + String(motor2State.speed) + "%, Duration: " + String(rampDuration) + "ms");
    } else {
      motor2State.targetSpeed = motor2State.speed;
      motor2State.rampActive = false;
      debugPrint("Motor2 ON - STANDARD SMOOTH Target Speed: " + String(motor2State.speed) + "%, Dir: " + String(motor2State.direction));
    }
    
    hardwareOff = false;

  } else if (strcmp(command, "OFF") == 0) {
    motor2State.enabled = false;
    motor2State.speed = 0;
    motor2State.targetSpeed = 0;
    motor2State.pendingDirectionChange = false;
    motor2State.rampActive = false;
    debugPrint("Motor2 OFF - smooth stopping...");

  } else if (strcmp(command, "SPEED") == 0) {
    if (motor2State.enabled) {
      motor2State.speed = atoi(speed);
      motor2State.targetSpeed = motor2State.speed;
      motor2State.rampActive = false;
      debugPrint("Motor2 speed target set to: " + String(motor2State.speed) + "%");
    } else {
      debugPrint("Motor2 not enabled, ignoring speed command");
    }

  } else if (strcmp(command, "DIR") == 0) {
    if (motor2State.enabled) {
      motor2State.rampActive = false;
      char newDir = direction[0];

      if (motor2State.direction == newDir) {
        debugPrint("Motor2 already running in direction: " + String(newDir));
        return;
      }

      if (motor2State.currentSpeed > 0) {
        motor2State.savedSpeed = motor2State.speed;
        motor2State.newDirection = newDir;
        motor2State.pendingDirectionChange = true;
        motor2State.targetSpeed = 0;
        debugPrint("Motor2 stopping for direction change from " + String(motor2State.direction) + " to " + String(newDir));
      } else {
        motor2State.direction = newDir;
        debugPrint("Motor2 direction changed to: " + String(newDir) + " (motor was stopped)");
      }
    } else {
      debugPrint("Motor2 not enabled, ignoring direction command");
    }

  } else {
    debugPrint("Unknown motor2 command: " + String(command));
  }
}

void turnOffHardware() {
  // Immediate shutdown for safety
  digitalWrite(MOTOR1_ENABLE_PIN, LOW);
  digitalWrite(MOTOR2_ENABLE_PIN, LOW);
  ledcWrite(MOTOR1_LEFT_PIN, 0);
  ledcWrite(MOTOR1_RIGHT_PIN, 0);
  ledcWrite(MOTOR2_LEFT_PIN, 0);
  ledcWrite(MOTOR2_RIGHT_PIN, 0);

  // Reset motor states (vrátane nových polí pre rampu)
  motor1State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};
  motor2State = {false, 0, 0, 0, 'S', 0, false, 0, 0, false, 0, 0, 0};

  debugPrint("All motors turned OFF due to disconnection");
  hardwareOff = true;
}