/*
  Waveshare DI end-stop input test.

  Target board:
    Waveshare Industrial ESP32-S3 Control Board With 8-Channel Digital Input
    & Output, built-in Xtensa 32-bit LX7 dual-core processor, up to 240 MHz,
    with multiple isolation protection circuits.

  Purpose:
    This sketch only reads the isolated DI terminals and prints which inputs
    are active in the Arduino IDE Serial Monitor. It does not start motors,
    write PWM, use MQTT, or drive any DO outputs.

  Window end-stop assignment used by the main window firmware:
    DI1 / D1 / GPIO4  = left window OPEN end-stop
    DI2 / D2 / GPIO5  = left window CLOSE end-stop
    DI3 / D3 / GPIO6  = right window OPEN end-stop
    DI4 / D4 / GPIO7  = right window CLOSE end-stop

  Remaining inputs are printed as spare diagnostics:
    DI5 / GPIO8, DI6 / GPIO9, DI7 / GPIO10, DI8 / GPIO11

  ACTIVE_LOW=true matches the current production firmware expectation for
  NC/active-low end-stops on the Waveshare isolated DI terminal block. If your
  measured wiring reports the opposite, set ACTIVE_LOW=false for this test.
*/

#include <Arduino.h>

constexpr unsigned long SERIAL_BAUD = 115200;
constexpr unsigned long POLL_INTERVAL_MS = 100;
constexpr unsigned long SNAPSHOT_INTERVAL_MS = 2000;
constexpr bool ACTIVE_LOW = true;
constexpr int DI_INPUT_MODE = INPUT;

struct DiInput {
  uint8_t number;
  uint8_t gpio;
  const char* role;
};

const DiInput DI_INPUTS[] = {
  {1, 4, "left window OPEN end-stop"},
  {2, 5, "left window CLOSE end-stop"},
  {3, 6, "right window OPEN end-stop"},
  {4, 7, "right window CLOSE end-stop"},
  {5, 8, "spare DI5"},
  {6, 9, "spare DI6"},
  {7, 10, "spare DI7"},
  {8, 11, "spare DI8"},
};

const size_t DI_COUNT = sizeof(DI_INPUTS) / sizeof(DI_INPUTS[0]);
bool lastActive[DI_COUNT];
bool firstSnapshot = true;
unsigned long lastPollAt = 0;
unsigned long lastSnapshotAt = 0;

bool isActiveLevel(int rawLevel) {
  return ACTIVE_LOW ? (rawLevel == LOW) : (rawLevel == HIGH);
}

const char* rawLevelText(int rawLevel) {
  return rawLevel == LOW ? "LOW" : "HIGH";
}

void printInputLine(size_t index, bool active, int rawLevel) {
  const DiInput& input = DI_INPUTS[index];
  Serial.print("DI");
  Serial.print(input.number);
  Serial.print(" / GPIO");
  Serial.print(input.gpio);
  Serial.print(" = ");
  Serial.print(active ? "ACTIVE" : "idle");
  Serial.print(" (raw ");
  Serial.print(rawLevelText(rawLevel));
  Serial.print(") - ");
  Serial.println(input.role);
}

void printActiveSummary() {
  bool anyActive = false;

  Serial.println("--- Active DI inputs ---");
  for (size_t i = 0; i < DI_COUNT; i++) {
    int rawLevel = digitalRead(DI_INPUTS[i].gpio);
    bool active = isActiveLevel(rawLevel);
    if (!active) continue;

    anyActive = true;
    printInputLine(i, active, rawLevel);
  }

  if (!anyActive) {
    Serial.println("No DI inputs are active.");
  }
}

void printFullSnapshot() {
  Serial.println("--- Full DI snapshot ---");
  for (size_t i = 0; i < DI_COUNT; i++) {
    int rawLevel = digitalRead(DI_INPUTS[i].gpio);
    bool active = isActiveLevel(rawLevel);
    printInputLine(i, active, rawLevel);
  }
}

bool pollForChanges() {
  bool changed = false;

  for (size_t i = 0; i < DI_COUNT; i++) {
    int rawLevel = digitalRead(DI_INPUTS[i].gpio);
    bool active = isActiveLevel(rawLevel);
    if (firstSnapshot || active != lastActive[i]) {
      lastActive[i] = active;
      changed = true;
    }
  }

  firstSnapshot = false;
  return changed;
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(500);

  for (size_t i = 0; i < DI_COUNT; i++) {
    pinMode(DI_INPUTS[i].gpio, DI_INPUT_MODE);
    lastActive[i] = false;
  }

  Serial.println();
  Serial.println("Waveshare Industrial ESP32-S3 DI end-stop test");
  Serial.println("Baud: 115200");
  Serial.println(ACTIVE_LOW ? "Active logic: LOW = active" : "Active logic: HIGH = active");
  Serial.println("Input mode: INPUT for isolated Waveshare DI terminals");
  Serial.println("If reading bare ESP32 GPIO pins instead of DI terminals, use INPUT_PULLUP as needed.");
  printFullSnapshot();
  printActiveSummary();
}

void loop() {
  unsigned long now = millis();

  if (now - lastPollAt >= POLL_INTERVAL_MS) {
    lastPollAt = now;
    if (pollForChanges()) {
      printActiveSummary();
    }
  }

  if (now - lastSnapshotAt >= SNAPSHOT_INTERVAL_MS) {
    lastSnapshotAt = now;
    printActiveSummary();
  }
}