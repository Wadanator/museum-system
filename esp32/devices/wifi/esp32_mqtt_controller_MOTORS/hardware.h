#ifndef HARDWARE_H
#define HARDWARE_H

// Hardware control functions
void initializeHardware();

// PWM Motor control functions
void controlMotor1(const char* command, const char* speed = "50", const char* direction = "L");
void controlMotor2(const char* command, const char* speed = "50", const char* direction = "L");

void turnOffHardware();

// Hardware state
extern bool hardwareOff;

// Motor state tracking
struct MotorState {
  bool enabled;
  int speed;
  int currentSpeed;  // Aktuálna PWM rýchlosť (pre smooth transition)
  int targetSpeed;   // Cieľová rýchlosť
  char direction;
  unsigned long lastUpdate;  // Čas posledného update
};

extern MotorState motor1State;
extern MotorState motor2State;

// Smooth control function - volaj v main loop
void updateMotorSmoothly();

#endif