#include "pwm_driver.h"
#include "config.h"
#include "debug.h"

static const uint8_t MAX_PWM_CHANNELS = 8;
static const unsigned long MODBUS_RESPONSE_TIMEOUT_MS = 500;
static const uint8_t MODBUS_RESPONSE_LEN = 8;

static HardwareSerial rs485Serial(1);
static bool pwmDriverInitialized = false;
static uint16_t currentDuties[MAX_PWM_CHANNELS];

const char* pwmResultText(PwmResult result) {
  switch (result) {
    case PWM_RESULT_OK: return "OK";
    case PWM_RESULT_INVALID_CHANNEL: return "ERROR:INVALID_CHANNEL";
    case PWM_RESULT_INVALID_DUTY: return "ERROR:INVALID_DUTY";
    case PWM_RESULT_WRITE_FAILED: return "ERROR:HARDWARE";
    default: return "ERROR";
  }
}

static uint16_t modbusCrc(const uint8_t* data, size_t len) {
  uint16_t crc = 0xFFFF;
  for (size_t pos = 0; pos < len; pos++) {
    crc ^= data[pos];
    for (uint8_t i = 0; i < 8; i++) {
      if (crc & 0x0001) {
        crc >>= 1;
        crc ^= 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  return crc;
}

static void appendCrc(uint8_t* frame, size_t lenWithoutCrc) {
  uint16_t crc = modbusCrc(frame, lenWithoutCrc);
  frame[lenWithoutCrc] = crc & 0xFF;
  frame[lenWithoutCrc + 1] = (crc >> 8) & 0xFF;
}

static void debugFrame(const char* label, const uint8_t* frame, size_t len) {
  if (!DEBUG) return;

  String line(label);
  for (size_t i = 0; i < len; i++) {
    if (frame[i] < 0x10) line += '0';
    line += String(frame[i], HEX);
    line += ' ';
  }
  debugPrint(line);
}

static PwmResult sendModbusFrame(const uint8_t* frame, size_t frameLen, uint8_t expectedFunction) {
  uint8_t response[32];
  size_t responseLen = 0;

  while (rs485Serial.available()) rs485Serial.read();
  debugFrame("PWM TX: ", frame, frameLen);

  if (RS485_DE_PIN >= 0) {
    digitalWrite(RS485_DE_PIN, HIGH);
    delayMicroseconds(80);
  }

  rs485Serial.write(frame, frameLen);
  rs485Serial.flush();

  if (RS485_DE_PIN >= 0) {
    delayMicroseconds(120);
    digitalWrite(RS485_DE_PIN, LOW);
  }

  unsigned long startedAt = millis();
  while (millis() - startedAt < MODBUS_RESPONSE_TIMEOUT_MS) {
    while (rs485Serial.available()) {
      if (responseLen < sizeof(response)) {
        response[responseLen++] = rs485Serial.read();
      } else {
        rs485Serial.read();
      }
    }

    if (responseLen >= MODBUS_RESPONSE_LEN) break;
    delay(1);
  }

  if (responseLen == 0) {
    debugPrint("PWM RX: no response");
    return PWM_RESULT_WRITE_FAILED;
  }

  debugFrame("PWM RX: ", response, responseLen);

  if (responseLen < 5) {
    debugPrint("PWM RX error: response too short");
    return PWM_RESULT_WRITE_FAILED;
  }

  uint16_t expectedCrc = modbusCrc(response, responseLen - 2);
  uint16_t receivedCrc = response[responseLen - 2] | (response[responseLen - 1] << 8);
  if (expectedCrc != receivedCrc) {
    debugPrint("PWM RX error: CRC mismatch");
    return PWM_RESULT_WRITE_FAILED;
  }

  if (response[0] != PWM_MODBUS_ID) {
    debugPrint("PWM RX error: wrong Modbus ID");
    return PWM_RESULT_WRITE_FAILED;
  }

  if (response[1] & 0x80) {
    debugPrint("PWM RX error: Modbus exception " + String(response[2], HEX));
    return PWM_RESULT_WRITE_FAILED;
  }

  if (response[1] != expectedFunction) {
    debugPrint("PWM RX error: unexpected function " + String(response[1], HEX));
    return PWM_RESULT_WRITE_FAILED;
  }

  return PWM_RESULT_OK;
}

static uint16_t pwmChannelBaseRegister(uint8_t channel) {
  return PWM_REGISTER_BASE + (channel * PWM_CHANNEL_REGISTER_STRIDE);
}

static PwmResult writeMultipleRegisters(uint16_t startRegister, const uint16_t* values, uint16_t count) {
  if (count > 16) return PWM_RESULT_INVALID_CHANNEL;

  uint8_t frame[9 + 32] = {0};
  frame[0] = PWM_MODBUS_ID;
  frame[1] = 0x10;
  frame[2] = (startRegister >> 8) & 0xFF;
  frame[3] = startRegister & 0xFF;
  frame[4] = (count >> 8) & 0xFF;
  frame[5] = count & 0xFF;
  frame[6] = count * 2;

  for (uint16_t i = 0; i < count; i++) {
    frame[7 + i * 2] = (values[i] >> 8) & 0xFF;
    frame[8 + i * 2] = values[i] & 0xFF;
  }

  size_t lenWithoutCrc = 7 + count * 2;
  appendCrc(frame, lenWithoutCrc);
  return sendModbusFrame(frame, lenWithoutCrc + 2, 0x10);
}

static PwmResult applyAllPwmOutputs(const char* source) {
  if (PWM_CHANNEL_COUNT > MAX_PWM_CHANNELS) return PWM_RESULT_INVALID_CHANNEL;

  uint32_t frequencyValue = PWM_FREQUENCY_HZ * 100UL;
  uint16_t values[MAX_PWM_CHANNELS * 3];

  for (uint8_t channel = 0; channel < PWM_CHANNEL_COUNT; channel++) {
    uint8_t base = channel * PWM_CHANNEL_REGISTER_STRIDE;
    values[base] = (frequencyValue >> 16) & 0xFFFF;
    values[base + 1] = frequencyValue & 0xFFFF;
    values[base + 2] = currentDuties[channel];
  }

  debugPrint(
    "PWM apply " + String(source) +
    ": " + String(PWM_FREQUENCY_HZ) +
    "Hz, duties=[" +
    String(currentDuties[0]) + "," +
    String(PWM_CHANNEL_COUNT > 1 ? currentDuties[1] : 0) + "," +
    String(PWM_CHANNEL_COUNT > 2 ? currentDuties[2] : 0) + "," +
    String(PWM_CHANNEL_COUNT > 3 ? currentDuties[3] : 0) +
    "]"
  );

  return writeMultipleRegisters(
    PWM_REGISTER_BASE,
    values,
    PWM_CHANNEL_COUNT * PWM_CHANNEL_REGISTER_STRIDE
  );
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

  for (uint8_t channel = 0; channel < MAX_PWM_CHANNELS; channel++) {
    currentDuties[channel] = PWM_DUTY_OFF;
  }

  pwmDriverInitialized = true;
  debugPrint("PWM raw Modbus driver initialized: ID " + String(PWM_MODBUS_ID));
}

PwmResult configureAllPwmFrequencies() {
  if (!pwmDriverInitialized) {
    initializePwmDriver();
  }

  for (uint8_t channel = 0; channel < MAX_PWM_CHANNELS; channel++) {
    currentDuties[channel] = PWM_DUTY_OFF;
  }

  return applyAllPwmOutputs("configure");
}

PwmResult writePwmChannel(uint8_t channel, uint16_t duty) {
  if (channel >= PWM_CHANNEL_COUNT || channel >= MAX_PWM_CHANNELS) {
    return PWM_RESULT_INVALID_CHANNEL;
  }

  if (duty > PWM_DUTY_MAX) {
    return PWM_RESULT_INVALID_DUTY;
  }

  if (!pwmDriverInitialized) {
    initializePwmDriver();
  }

  currentDuties[channel] = duty;
  debugPrint(
    "PWM D" + String(channel + 1) +
    " duty request: reg=0x" +
    String(pwmChannelBaseRegister(channel) + PWM_DUTY_REGISTER_OFFSET, HEX) +
    ", duty=" +
    String(duty)
  );

  return applyAllPwmOutputs("duty");
}

PwmResult writeAllPwmChannelsOff() {
  if (!pwmDriverInitialized) {
    initializePwmDriver();
  }

  for (uint8_t channel = 0; channel < MAX_PWM_CHANNELS; channel++) {
    currentDuties[channel] = PWM_DUTY_OFF;
  }

  return applyAllPwmOutputs("all_off");
}
