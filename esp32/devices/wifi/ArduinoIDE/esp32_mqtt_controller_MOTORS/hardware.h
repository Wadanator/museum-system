#ifndef HARDWARE_H
#define HARDWARE_H

// Hardware control functions
void initializeHardware();

// ZMENENÉ: Pridanie voliteľného rampTime parametra
void controlMotor1(const char* command, const char* speed = "50", const char* direction = "L", const char* rampTime = "0");
void controlMotor2(const char* command, const char* speed = "50", const char* direction = "L", const char* rampTime = "0");

void turnOffHardware();

// Hardware state
extern bool hardwareOff;

// Motor state tracking - ROZŠÍRENÉ pre správnu zmenu smeru
struct MotorState {
  bool enabled;
  int speed;
  int currentSpeed;        // Aktuálna PWM rýchlosť (pre smooth transition)
  int targetSpeed;         // Cieľová rýchlosť
  char direction;          // Aktuálny smer ('L' alebo 'R')
  unsigned long lastUpdate;  // Čas posledného update
  
  // NOVÉ polia pre zmenu smeru:
  bool pendingDirectionChange;  // Či čaká na zmenu smeru
  char newDirection;            // Nový smer na ktorý sa má zmeniť
  int savedSpeed;              // Uložená rýchlosť pred zmenou smeru

  // NOVÉ polia pre DEFINOVANÝ ROZBEH (RAMP UP):
  bool rampActive;             // Či beží custom rozbeh/spomalenie
  unsigned long rampStartTime;   // Čas spustenia rampy
  unsigned long rampDurationMs;  // Požadovaný čas trvania rampy (5000 = 5s)
  int rampStartSpeed;          // Rýchlosť, z ktorej sa rampa začala
};

extern MotorState motor1State;
extern MotorState motor2State;

// Smooth control function - volaj v main loop
void updateMotorSmoothly();

#endif