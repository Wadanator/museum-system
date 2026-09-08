#ifndef HARDWARE_H
#define HARDWARE_H

// Hardware control interface.
void initializeHardware();

bool controlMotor1(const char* command, const char* speed = "50", const char* direction = "L", const char* rampTime = "0");
bool controlMotor2(const char* command, const char* speed = "50", const char* direction = "L", const char* rampTime = "0");

void turnOffHardware();

// Hardware state.
extern bool hardwareOff;

// Runtime state for one bidirectional PWM motor.
struct MotorState {
  bool enabled;
  int speed;
  int currentSpeed;        // Current PWM speed used by the smooth updater.
  int targetSpeed;         // Requested final speed.
  char direction;          // Current direction: 'L', 'R', or 'S'.
  unsigned long lastUpdate;  // Timestamp of the last PWM update.
  
  bool pendingDirectionChange;  // Direction changes complete after speed reaches zero.
  char newDirection;            // Direction requested for the next motion phase.
  int savedSpeed;               // Speed restored after a controlled direction change.

  bool rampActive;              // A command-defined ramp is in progress.
  unsigned long rampStartTime;  // Timestamp when the ramp started.
  unsigned long rampDurationMs; // Requested ramp duration in milliseconds.
  int rampStartSpeed;           // Speed at the beginning of the ramp.
};

extern MotorState motor1State;
extern MotorState motor2State;

void updateMotorSmoothly();

#endif
