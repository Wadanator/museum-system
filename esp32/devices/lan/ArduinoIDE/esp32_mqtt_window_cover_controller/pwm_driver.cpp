#include "pwm_driver.h"
#include "config.h"
#include "debug.h"
#include <ModbusMaster.h>

static HardwareSerial rs485Serial(1);
static ModbusMaster pwmNode;
static bool pwmDriverInitialized = false;

static void rs485PreTransmission() {
  if (RS485_DE_PIN >= 0) {
    digitalWrite(RS485_DE_PIN, HIGH);
  }
}

static void rs485PostTransmission() {
  if (RS485_DE_PIN >= 0) {
    digitalWrite(RS485_DE_PIN, LOW);
  }
}

const char* pwmResultText(PwmResult result) {
  switch (result) {
    case PWM_RESULT_OK: return "OK";
    case PWM_RESULT_INVALID_CHANNEL: return "ERROR:INVALID_CHANNEL";
    case PWM_RESULT_INVALID_DUTY: return "ERROR:INVALID_DUTY";
    case PWM_RESULT_WRITE_FAILED: return "ERROR:HARDWARE";
    default: return "ERROR";
  }
}

void initializePwmDriver() {
  if (RS485_DE_PIN >= 0) {
    pinMode(RS485_DE_PIN, OUTPUT);
    digitalWrite(RS485_DE_PIN, LOW);
  }

  rs485Serial.begin(
    RS485_BAUD_RATE,
    RS485_SERIAL_CONFIG,
    RS485_RX_PIN,
    RS485_TX_PIN
  );

  pwmNode.begin(PWM_MODBUS_ID, rs485Serial);
  if (RS485_DE_PIN >= 0) {
    pwmNode.preTransmission(rs485PreTransmission);
    pwmNode.postTransmission(rs485PostTransmission);
  }

  pwmDriverInitialized = true;
  debugPrint("PWM Modbus driver initialized: ID " + String(PWM_MODBUS_ID));
}

static uint16_t pwmChannelBaseRegister(uint8_t channel) {
  return PWM_REGISTER_BASE + (channel * PWM_CHANNEL_REGISTER_STRIDE);
}

static uint16_t pwmDutyRegister(uint8_t channel) {
  return pwmChannelBaseRegister(channel) + PWM_DUTY_REGISTER_OFFSET;
}

static PwmResult configurePwmFrequency(uint8_t channel) {
  if (channel >= PWM_CHANNEL_COUNT) {
    return PWM_RESULT_INVALID_CHANNEL;
  }

  if (!pwmDriverInitialized) {
    initializePwmDriver();
  }

  uint32_t frequencyValue = PWM_FREQUENCY_HZ * 100UL;
  uint16_t highWord = (frequencyValue >> 16) & 0xFFFF;
  uint16_t lowWord = frequencyValue & 0xFFFF;
  uint16_t frequencyRegister = pwmChannelBaseRegister(channel);

  pwmNode.setTransmitBuffer(0, highWord);
  pwmNode.setTransmitBuffer(1, lowWord);

  uint8_t result = pwmNode.writeMultipleRegisters(frequencyRegister, 2);
  if (result != pwmNode.ku8MBSuccess) {
    debugPrint(
      "PWM frequency write failed: ch=" + String(channel + 1) +
      ", reg=0x" + String(frequencyRegister, HEX) +
      ", hz=" + String(PWM_FREQUENCY_HZ) +
      ", rc=" + String(result)
    );
    return PWM_RESULT_WRITE_FAILED;
  }

  return PWM_RESULT_OK;
}

PwmResult configureAllPwmFrequencies() {
  PwmResult finalResult = PWM_RESULT_OK;

  for (uint8_t channel = 0; channel < PWM_CHANNEL_COUNT; channel++) {
    PwmResult result = configurePwmFrequency(channel);
    if (result != PWM_RESULT_OK) {
      finalResult = result;
    }
  }

  return finalResult;
}

PwmResult writePwmChannel(uint8_t channel, uint16_t duty) {
  if (channel >= PWM_CHANNEL_COUNT) {
    return PWM_RESULT_INVALID_CHANNEL;
  }

  if (duty > PWM_DUTY_MAX) {
    return PWM_RESULT_INVALID_DUTY;
  }

  if (!pwmDriverInitialized) {
    initializePwmDriver();
  }

  uint16_t pwmRegister = pwmDutyRegister(channel);
  uint8_t result = pwmNode.writeSingleRegister(pwmRegister, duty);
  if (result != pwmNode.ku8MBSuccess) {
    debugPrint(
      "PWM write failed: ch=" + String(channel + 1) +
      ", reg=0x" + String(pwmRegister, HEX) +
      ", duty=" + String(duty) +
      ", rc=" + String(result)
    );
    return PWM_RESULT_WRITE_FAILED;
  }

  return PWM_RESULT_OK;
}

PwmResult writeAllPwmChannelsOff() {
  PwmResult finalResult = PWM_RESULT_OK;

  for (uint8_t channel = 0; channel < PWM_CHANNEL_COUNT; channel++) {
    PwmResult result = writePwmChannel(channel, PWM_DUTY_OFF);
    if (result != PWM_RESULT_OK) {
      finalResult = result;
    }
  }

  return finalResult;
}
