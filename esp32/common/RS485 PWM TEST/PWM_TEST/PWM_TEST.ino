#include <HardwareSerial.h>

// Standalone HW test for Waveshare Modbus RTU PWM Output 4CH.
// Upload this sketch only when the H-bridges/motors are disconnected.
// It forces D1..D4 to 20 kHz and 100 % duty so a multimeter should see
// the selected output level, typically 3.3 V or 5 V, between Dx and GND.

static const int RS485_RX_PIN = 18;
static const int RS485_TX_PIN = 17;
static const int RS485_DE_PIN = 21;

static const uint8_t PWM_MODBUS_ID = 1;
static const unsigned long RS485_BAUD_RATE = 9600;

static const uint16_t PWM_REGISTER_BASE = 0x0000;
static const uint8_t PWM_CHANNEL_COUNT = 4;
static const uint8_t PWM_CHANNEL_REGISTER_STRIDE = 3;
static const uint8_t PWM_DUTY_REGISTER_OFFSET = 2;

static const uint32_t PWM_FREQUENCY_HZ = 20000;
static const uint16_t PWM_DUTY_OFF = 0;
static const uint16_t PWM_DUTY_MAX = 5000;  // 100.00 %

HardwareSerial RS485(1);

uint16_t modbusCrc(const uint8_t* data, size_t len) {
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

void appendCrc(uint8_t* frame, size_t lenWithoutCrc) {
  uint16_t crc = modbusCrc(frame, lenWithoutCrc);
  frame[lenWithoutCrc] = crc & 0xFF;
  frame[lenWithoutCrc + 1] = (crc >> 8) & 0xFF;
}

void printFrame(const char* label, const uint8_t* frame, size_t len) {
  Serial.print(label);
  for (size_t i = 0; i < len; i++) {
    if (frame[i] < 0x10) Serial.print('0');
    Serial.print(frame[i], HEX);
    Serial.print(' ');
  }
  Serial.println();
}

bool sendFrame(const uint8_t* frame, size_t len, uint8_t* response, size_t responseSize, size_t& responseLen) {
  responseLen = 0;
  while (RS485.available()) RS485.read();

  printFrame("TX: ", frame, len);

  digitalWrite(RS485_DE_PIN, HIGH);
  delayMicroseconds(80);
  RS485.write(frame, len);
  RS485.flush();
  delayMicroseconds(120);
  digitalWrite(RS485_DE_PIN, LOW);

  unsigned long start = millis();
  while (millis() - start < 500) {
    while (RS485.available()) {
      if (responseLen < responseSize) {
        response[responseLen++] = RS485.read();
      } else {
        RS485.read();
      }
    }
  }

  if (responseLen == 0) {
    Serial.println("RX: no response");
    return false;
  }

  printFrame("RX: ", response, responseLen);

  if (responseLen < 5) {
    Serial.println("RX ERROR: too short");
    return false;
  }

  uint16_t expectedCrc = modbusCrc(response, responseLen - 2);
  uint16_t receivedCrc = response[responseLen - 2] | (response[responseLen - 1] << 8);
  if (expectedCrc != receivedCrc) {
    Serial.println("RX ERROR: CRC mismatch");
    return false;
  }

  if (response[0] != PWM_MODBUS_ID) {
    Serial.println("RX ERROR: wrong Modbus ID");
    return false;
  }

  if (response[1] & 0x80) {
    Serial.print("RX ERROR: Modbus exception ");
    Serial.println(response[2], HEX);
    return false;
  }

  return true;
}

bool writeMultipleRegisters(uint16_t startRegister, const uint16_t* values, uint16_t count) {
  if (count > 16) return false;

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

  uint8_t response[32];
  size_t responseLen = 0;
  return sendFrame(frame, lenWithoutCrc + 2, response, sizeof(response), responseLen);
}

bool writeSingleRegister(uint16_t reg, uint16_t value) {
  uint8_t frame[8] = {
    PWM_MODBUS_ID,
    0x06,
    (uint8_t)((reg >> 8) & 0xFF),
    (uint8_t)(reg & 0xFF),
    (uint8_t)((value >> 8) & 0xFF),
    (uint8_t)(value & 0xFF),
    0,
    0
  };
  appendCrc(frame, 6);

  uint8_t response[32];
  size_t responseLen = 0;
  return sendFrame(frame, sizeof(frame), response, sizeof(response), responseLen);
}

uint16_t channelBaseRegister(uint8_t channel) {
  return PWM_REGISTER_BASE + channel * PWM_CHANNEL_REGISTER_STRIDE;
}

uint16_t channelDutyRegister(uint8_t channel) {
  return channelBaseRegister(channel) + PWM_DUTY_REGISTER_OFFSET;
}

bool setChannelFrequency(uint8_t channel, uint32_t frequencyHz) {
  uint32_t frequencyValue = frequencyHz * 100UL;  // module unit is 0.01 Hz
  uint16_t values[2] = {
    (uint16_t)((frequencyValue >> 16) & 0xFFFF),
    (uint16_t)(frequencyValue & 0xFFFF)
  };

  Serial.print("Set CH");
  Serial.print(channel + 1);
  Serial.print(" frequency = ");
  Serial.print(frequencyHz);
  Serial.println(" Hz");

  return writeMultipleRegisters(channelBaseRegister(channel), values, 2);
}

bool setChannelDuty(uint8_t channel, uint16_t duty) {
  Serial.print("Set D");
  Serial.print(channel + 1);
  Serial.print(" duty = ");
  Serial.print(duty / 100.0f, 2);
  Serial.println(" %");

  return writeSingleRegister(channelDutyRegister(channel), duty);
}

void setAllOutputs(uint16_t duty) {
  uint32_t frequencyValue = PWM_FREQUENCY_HZ * 100UL;  // module unit is 0.01 Hz
  uint16_t values[PWM_CHANNEL_COUNT * PWM_CHANNEL_REGISTER_STRIDE];

  for (uint8_t ch = 0; ch < PWM_CHANNEL_COUNT; ch++) {
    uint8_t base = ch * PWM_CHANNEL_REGISTER_STRIDE;
    values[base] = (uint16_t)((frequencyValue >> 16) & 0xFFFF);
    values[base + 1] = (uint16_t)(frequencyValue & 0xFFFF);
    values[base + 2] = duty;
  }

  Serial.print("Set D1..D4 = ");
  Serial.print(PWM_FREQUENCY_HZ);
  Serial.print(" Hz / ");
  Serial.print(duty / 100.0f, 2);
  Serial.println(" % in one Function 16 frame");

  bool ok = writeMultipleRegisters(
    PWM_REGISTER_BASE,
    values,
    PWM_CHANNEL_COUNT * PWM_CHANNEL_REGISTER_STRIDE
  );

  Serial.println(ok ? "ALL CHANNELS OK" : "ERROR: Modbus command failed");
}

void readAllRegisters() {
  uint8_t frame[8] = {
    PWM_MODBUS_ID,
    0x03,
    0x00,
    0x00,
    0x00,
    PWM_CHANNEL_COUNT * PWM_CHANNEL_REGISTER_STRIDE,
    0,
    0
  };
  appendCrc(frame, 6);

  uint8_t response[80];
  size_t responseLen = 0;
  sendFrame(frame, sizeof(frame), response, sizeof(response), responseLen);
}

void printHelp() {
  Serial.println();
  Serial.println("Commands:");
  Serial.println("  MAX  - set D1..D4 to 20 kHz / 100 %");
  Serial.println("  OFF  - set D1..D4 duty to 0 %");
  Serial.println("  READ - read all PWM registers");
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("=== RS485 PWM OUTPUT 4CH HARD TEST ===");
  Serial.println("WARNING: disconnect H-bridges/motors before using MAX.");
  Serial.println("Target: D1..D4 = 20 kHz / 100 % duty.");

  pinMode(RS485_DE_PIN, OUTPUT);
  digitalWrite(RS485_DE_PIN, LOW);
  RS485.begin(RS485_BAUD_RATE, SERIAL_8N1, RS485_RX_PIN, RS485_TX_PIN);

  printHelp();
  setAllOutputs(PWM_DUTY_MAX);
}

void loop() {
  if (!Serial.available()) return;

  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toUpperCase();

  if (command == "MAX") {
    setAllOutputs(PWM_DUTY_MAX);
  } else if (command == "OFF") {
    setAllOutputs(PWM_DUTY_OFF);
  } else if (command == "READ") {
    readAllRegisters();
  } else if (command.length() > 0) {
    printHelp();
  }
}