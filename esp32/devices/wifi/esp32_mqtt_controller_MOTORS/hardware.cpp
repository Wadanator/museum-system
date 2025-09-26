#include "hardware.h"
#include "config.h"
#include "debug.h"
#include <Arduino.h>

// Global hardware state
bool hardwareOff = false;

// Motor state tracking
MotorState motor1State = {false, 0, 'S'};
MotorState motor2State = {false, 0, 'S'};

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

void controlMotor1(const char* command, const char* speed, const char* direction) {
  debugPrint("Motor1 command: " + String(command) + ", speed: " + String(speed) + ", dir: " + String(direction));
  
  if (strcmp(command, "ON") == 0) {
    motor1State.enabled = true;
    motor1State.speed = atoi(speed);
    motor1State.direction = direction[0];
    digitalWrite(MOTOR1_ENABLE_PIN, HIGH);
    updateMotorPWM(1, motor1State.speed, motor1State.direction);
    debugPrint("Motor1 ON - Speed: " + String(motor1State.speed) + "%, Dir: " + String(motor1State.direction));
    hardwareOff = false;
    
  } else if (strcmp(command, "OFF") == 0) {
    motor1State.enabled = false;
    motor1State.speed = 0;
    digitalWrite(MOTOR1_ENABLE_PIN, LOW);
    updateMotorPWM(1, 0, 'S');
    debugPrint("Motor1 OFF");
    
  } else if (strcmp(command, "SPEED") == 0) {
    if (motor1State.enabled) {
      motor1State.speed = atoi(speed);
      updateMotorPWM(1, motor1State.speed, motor1State.direction);
      debugPrint("Motor1 speed set to: " + String(motor1State.speed) + "%");
    } else {
      debugPrint("Motor1 not enabled, ignoring speed command");
    }
    
  } else if (strcmp(command, "DIR") == 0) {
    if (motor1State.enabled) {
      motor1State.direction = direction[0];
      updateMotorPWM(1, motor1State.speed, motor1State.direction);
      debugPrint("Motor1 direction set to: " + String(motor1State.direction));
    } else {
      debugPrint("Motor1 not enabled, ignoring direction command");
    }
    
  } else {
    debugPrint("Unknown motor1 command: " + String(command));
  }
}

void controlMotor2(const char* command, const char* speed, const char* direction) {
  debugPrint("Motor2 command: " + String(command) + ", speed: " + String(speed) + ", dir: " + String(direction));
  
  if (strcmp(command, "ON") == 0) {
    motor2State.enabled = true;
    motor2State.speed = atoi(speed);
    motor2State.direction = direction[0];
    digitalWrite(MOTOR2_ENABLE_PIN, HIGH);
    updateMotorPWM(2, motor2State.speed, motor2State.direction);
    debugPrint("Motor2 ON - Speed: " + String(motor2State.speed) + "%, Dir: " + String(motor2State.direction));
    hardwareOff = false;
    
  } else if (strcmp(command, "OFF") == 0) {
    motor2State.enabled = false;
    motor2State.speed = 0;
    digitalWrite(MOTOR2_ENABLE_PIN, LOW);
    updateMotorPWM(2, 0, 'S');
    debugPrint("Motor2 OFF");
    
  } else if (strcmp(command, "SPEED") == 0) {
    if (motor2State.enabled) {
      motor2State.speed = atoi(speed);
      updateMotorPWM(2, motor2State.speed, motor2State.direction);
      debugPrint("Motor2 speed set to: " + String(motor2State.speed) + "%");
    } else {
      debugPrint("Motor2 not enabled, ignoring speed command");
    }
    
  } else if (strcmp(command, "DIR") == 0) {
    if (motor2State.enabled) {
      motor2State.direction = direction[0];
      updateMotorPWM(2, motor2State.speed, motor2State.direction);
      debugPrint("Motor2 direction set to: " + String(motor2State.direction));
    } else {
      debugPrint("Motor2 not enabled, ignoring direction command");
    }
    
  } else {
    debugPrint("Unknown motor2 command: " + String(command));
  }
}

void turnOffHardware() {
  // Motors
  digitalWrite(MOTOR1_ENABLE_PIN, LOW);
  digitalWrite(MOTOR2_ENABLE_PIN, LOW);
  ledcWrite(MOTOR1_LEFT_PIN, 0);
  ledcWrite(MOTOR1_RIGHT_PIN, 0);
  ledcWrite(MOTOR2_LEFT_PIN, 0);
  ledcWrite(MOTOR2_RIGHT_PIN, 0);
  
  // Reset motor states
  motor1State = {false, 0, 'S'};
  motor2State = {false, 0, 'S'};
  
  debugPrint("All motors turned OFF due to disconnection");
  hardwareOff = true;
}