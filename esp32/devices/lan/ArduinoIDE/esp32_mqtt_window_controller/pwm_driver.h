#ifndef PWM_DRIVER_H
#define PWM_DRIVER_H

#include <Arduino.h>

enum PwmResult : uint8_t {
  PWM_RESULT_OK = 0,
  PWM_RESULT_INVALID_CHANNEL,
  PWM_RESULT_INVALID_DUTY,
  PWM_RESULT_WRITE_FAILED
};

void initializePwmDriver();
PwmResult configureAllPwmFrequencies();
PwmResult writePwmChannel(uint8_t channel, uint16_t duty);
PwmResult writeAllPwmChannelsOff();
const char* pwmResultText(PwmResult result);

#endif
