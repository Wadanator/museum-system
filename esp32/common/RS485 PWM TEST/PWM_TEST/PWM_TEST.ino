#include <HardwareSerial.h>

#define RXD1    18
#define TXD1    17
#define TXD1EN  21

HardwareSerial RS485(1);

uint8_t frame[] = {0x01, 0x03, 0x00, 0x00, 0x00, 0x0C, 0x45, 0xCF};

uint16_t modbusCRC(uint8_t *buf, int len) {
  uint16_t crc = 0xFFFF;
  for (int pos = 0; pos < len; pos++) {
    crc ^= (uint16_t)buf[pos];
    for (int i = 0; i < 8; i++) {
      if (crc & 0x0001) { crc >>= 1; crc ^= 0xA001; }
      else crc >>= 1;
    }
  }
  return crc;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  RS485.begin(9600, SERIAL_8N1, RXD1, TXD1);

  // KĽÚČOVÉ: nastavenie DE pinu a hardvérového RS485 half-duplex módu
  if (!RS485.setPins(-1, -1, -1, TXD1EN)) {
    Serial.println("Failed to set TXDEN pin!");
  }
  if (!RS485.setMode(UART_MODE_RS485_HALF_DUPLEX)) {
    Serial.println("Failed to set RS485 mode!");
  }

  Serial.println("RS485 init OK, start test");
}

void loop() {
  Serial.print("TX: ");
  for (int i = 0; i < 8; i++) Serial.printf("%02X ", frame[i]);
  Serial.println();

  while (RS485.available()) RS485.read();

  unsigned long t0 = micros();
  RS485.write(frame, sizeof(frame));
  RS485.flush();
  unsigned long txDoneAt = micros();
  Serial.printf("TX trvalo: %lu us\n", txDoneAt - t0);

  unsigned long start = millis();
  uint8_t buf[64];
  int len = 0;
  unsigned long firstByteAt = 0;

  while (millis() - start < 1000) {
    if (RS485.available()) {
      if (len == 0) firstByteAt = micros();
      while (RS485.available() && len < (int)sizeof(buf)) {
        buf[len++] = RS485.read();
      }
    }
  }

  if (len == 0) {
    Serial.println("Naozaj nic.");
  } else {
    Serial.printf("Prijatych %d bajtov, prvy prisiel %lu us po TX: ", len, firstByteAt - txDoneAt);
    for (int j = 0; j < len; j++) Serial.printf("%02X ", buf[j]);
    Serial.println();

    if (len >= 3) {
      uint16_t rxCrc = modbusCRC(buf, len - 2);
      uint16_t recvCrc = buf[len - 2] | (buf[len - 1] << 8);
      Serial.println(rxCrc == recvCrc ? "CRC OK" : "CRC CHYBA");
    }
  }

  delay(3000);
}