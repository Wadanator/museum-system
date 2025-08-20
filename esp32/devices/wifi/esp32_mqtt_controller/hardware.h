#ifndef HARDWARE_H
#define HARDWARE_H

// Hardware control functions
void initializeHardware();
void controlMotor(const char* command);
void controlLight(const char* command);
void controlSteam(const char* command);
void turnOffHardware();

// Hardware state
extern bool hardwareOff;

#endif