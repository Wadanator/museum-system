#include "serial_console.h"

#include <Arduino.h>
#include <string.h>

#include "config.h"
#include "hardware.h"
#include "mqtt_manager.h"

namespace {

constexpr int TARGET_INVALID = -1;
constexpr int TARGET_ALL = -2;
constexpr size_t MAX_CONSOLE_LINE = 96;
constexpr int MAX_TOKENS = 4;

String inputBuffer;
bool serialManualControlActive = false;
unsigned long lastSerialManualCommandAt = 0;

bool isOk(const char* feedback) {
  return feedback != nullptr && strcmp(feedback, "OK") == 0;
}

void printHelp() {
  Serial.println();
  Serial.println("Serial console manual control");
  Serial.println("Type one command and press Enter. Speed is optional for OPEN/CLOSE.");
  Serial.println();
  Serial.println("Commands you can type:");
  Serial.println("  help                         show this command list");
  Serial.println("  status                       print current window state");
  Serial.println("  open left                    open the left window");
  Serial.println("  close left                   close the left window");
  Serial.println("  open right                   open the right window");
  Serial.println("  close right                  close the right window");
  Serial.println("  open left 30                 open left window at 30 percent speed");
  Serial.println("  close right 50               close right window at 50 percent speed");
  Serial.println("  stop left                    stop only the left window");
  Serial.println("  stop right                   stop only the right window");
  Serial.println("  stop                         stop all windows");
  Serial.println("  open all 30                  open both windows at 30 percent speed");
  Serial.println("  close all 30                 close both windows at 30 percent speed");
  Serial.println("  speed left 40                change left speed to 40 percent");
  Serial.println();
  Serial.println("Also accepted:");
  Serial.println("  left open [speed]            same as open left [speed]");
  Serial.println("  right close [speed]          same as close right [speed]");
  Serial.println("  l / r                        short names for left / right");
  Serial.println("  lava / prava                 Slovak aliases for left / right");
  Serial.println("  otvor / zatvor / zastav      Slovak aliases for open / close / stop");
  Serial.println("Safety: uses the same firmware path as MQTT: dead-time, maxMoveMs, and end-stops if enabled.");
  Serial.println();
}

void printSideStatus(int sideIndex) {
  if (sideIndex < 0 || sideIndex >= WINDOW_SIDE_COUNT || !WINDOW_SIDES[sideIndex].enabled) return;

  Serial.print("  ");
  Serial.print(WINDOW_SIDES[sideIndex].topicName);
  Serial.print(" state=");
  Serial.print(getWindowStateText(sideIndex));
  Serial.print(" direction=");
  Serial.print(getWindowDirectionText(sideIndex));
  Serial.print(" speed=");
  Serial.print(getWindowSpeed(sideIndex));
  Serial.println("%");
}

void printAllStatus() {
  Serial.println("Window status:");
  for (int i = 0; i < WINDOW_SIDE_COUNT; i++) {
    printSideStatus(i);
  }
}

bool isAllToken(const String& token) {
  return token == "all" || token == "both" || token == "*" ||
         token == "window" || token == "windows" ||
         token == "vsetko" || token == "vsetky" || token == "obe";
}

bool isLeftAlias(const String& token) {
  return token == "l" || token == "left" || token == "lava" || token == "lavy";
}

bool isRightAlias(const String& token) {
  return token == "r" || token == "right" || token == "prava" || token == "pravy";
}

int resolveSideIndex(const String& token) {
  for (int i = 0; i < WINDOW_SIDE_COUNT; i++) {
    if (!WINDOW_SIDES[i].enabled) continue;

    String topic = String(WINDOW_SIDES[i].topicName);
    topic.toLowerCase();
    int slashIndex = topic.lastIndexOf('/');
    String shortName = slashIndex >= 0 ? topic.substring(slashIndex + 1) : topic;

    if (token == String(i + 1) || token == topic || token == shortName || token.endsWith(topic)) {
      return i;
    }
    if (shortName == "left" && isLeftAlias(token)) return i;
    if (shortName == "right" && isRightAlias(token)) return i;
  }
  return TARGET_INVALID;
}

int resolveTarget(const String& token) {
  if (isAllToken(token)) return TARGET_ALL;
  return resolveSideIndex(token);
}

enum ConsoleAction {
  ACTION_UNKNOWN,
  ACTION_OPEN,
  ACTION_CLOSE,
  ACTION_STOP,
  ACTION_SPEED,
  ACTION_HELP,
  ACTION_STATUS
};

ConsoleAction parseAction(const String& token) {
  if (token == "help" || token == "?" || token == "h") return ACTION_HELP;
  if (token == "status" || token == "stav" || token == "s") return ACTION_STATUS;
  if (token == "open" || token == "otvor" || token == "otvorit") return ACTION_OPEN;
  if (token == "close" || token == "zatvor" || token == "zatvorit") return ACTION_CLOSE;
  if (token == "stop" || token == "off" || token == "zastav" || token == "stoj") return ACTION_STOP;
  if (token == "speed" || token == "rychlost" || token == "pwm") return ACTION_SPEED;
  return ACTION_UNKNOWN;
}

int splitTokens(String line, String tokens[], int maxTokens) {
  line.trim();
  line.toLowerCase();
  line.replace('\t', ' ');
  line.replace(',', ' ');

  int count = 0;
  int start = 0;
  while (start < line.length() && count < maxTokens) {
    while (start < line.length() && line.charAt(start) == ' ') start++;
    if (start >= line.length()) break;

    int end = start;
    while (end < line.length() && line.charAt(end) != ' ') end++;
    tokens[count++] = line.substring(start, end);
    start = end + 1;
  }
  return count;
}

bool runSideAction(int sideIndex, ConsoleAction action, const String& valueToken) {
  if (sideIndex < 0 || sideIndex >= WINDOW_SIDE_COUNT || !WINDOW_SIDES[sideIndex].enabled) {
    Serial.println("[SERIAL] ERROR: unknown or disabled side");
    return false;
  }

  const char* feedback = "ERROR";
  const char* value = valueToken.length() > 0 ? valueToken.c_str() : nullptr;

  switch (action) {
    case ACTION_OPEN:
      feedback = commandWindowOpen(sideIndex, value);
      break;
    case ACTION_CLOSE:
      feedback = commandWindowClose(sideIndex, value);
      break;
    case ACTION_STOP:
      feedback = commandWindowStop(sideIndex);
      break;
    case ACTION_SPEED:
      if (value == nullptr) {
        Serial.println("[SERIAL] ERROR: speed command needs value 0-100");
        return false;
      }
      feedback = commandWindowSpeed(sideIndex, value);
      break;
    default:
      Serial.println("[SERIAL] ERROR: unsupported action");
      return false;
  }

  Serial.print("[SERIAL] ");
  Serial.print(WINDOW_SIDES[sideIndex].topicName);
  Serial.print(" -> ");
  Serial.println(feedback);
  printSideStatus(sideIndex);
  return isOk(feedback);
}

void rememberSuccessfulManualCommand(ConsoleAction action) {
  lastCommandTime = millis();
  lastSerialManualCommandAt = lastCommandTime;

  if (action == ACTION_OPEN || action == ACTION_CLOSE || action == ACTION_SPEED) {
    serialManualControlActive = true;
  }
  if (action == ACTION_STOP || allWindowsStopped) {
    serialManualControlActive = !allWindowsStopped;
  }
}

void executeTargetAction(int target, ConsoleAction action, const String& valueToken) {
  bool anyOk = false;

  if (target == TARGET_ALL) {
    if (action == ACTION_STOP) {
      stopAllWindows("serial_console");
      lastCommandTime = millis();
      serialManualControlActive = false;
      Serial.println("[SERIAL] all windows -> OK");
      printAllStatus();
      return;
    }

    for (int i = 0; i < WINDOW_SIDE_COUNT; i++) {
      if (!WINDOW_SIDES[i].enabled) continue;
      anyOk = runSideAction(i, action, valueToken) || anyOk;
    }
  } else {
    anyOk = runSideAction(target, action, valueToken);
  }

  if (anyOk) {
    rememberSuccessfulManualCommand(action);
  }
}

void processLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  String tokens[MAX_TOKENS];
  int tokenCount = splitTokens(line, tokens, MAX_TOKENS);
  if (tokenCount == 0) return;

  ConsoleAction action = parseAction(tokens[0]);
  int target = TARGET_INVALID;
  String valueToken;

  if (action == ACTION_HELP) {
    printHelp();
    return;
  }
  if (action == ACTION_STATUS) {
    printAllStatus();
    return;
  }

  if (action != ACTION_UNKNOWN) {
    if (action == ACTION_STOP && tokenCount == 1) {
      target = TARGET_ALL;
    } else if (tokenCount >= 2) {
      target = resolveTarget(tokens[1]);
      if (tokenCount >= 3) valueToken = tokens[2];
    }
  } else {
    target = resolveTarget(tokens[0]);
    if (target != TARGET_INVALID && tokenCount >= 2) {
      action = parseAction(tokens[1]);
      if (tokenCount >= 3) valueToken = tokens[2];
    }
  }

  if (action == ACTION_UNKNOWN || action == ACTION_HELP || action == ACTION_STATUS) {
    Serial.println("[SERIAL] ERROR: unknown command. Type 'help'.");
    return;
  }

  if (target == TARGET_INVALID) {
    Serial.println("[SERIAL] ERROR: missing/unknown side. Use left, right, or all.");
    return;
  }

  executeTargetAction(target, action, valueToken);
}

}  // namespace

void initializeSerialConsole() {
  inputBuffer.reserve(MAX_CONSOLE_LINE);
  printHelp();
}

void handleSerialConsole() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());

    if (c == '\r') continue;
    if (c == '\n') {
      String line = inputBuffer;
      inputBuffer = "";
      processLine(line);
      continue;
    }

    if (c == '\b' || c == 127) {
      if (inputBuffer.length() > 0) {
        inputBuffer.remove(inputBuffer.length() - 1);
      }
      continue;
    }

    if (isPrintable(static_cast<unsigned char>(c))) {
      if (inputBuffer.length() < MAX_CONSOLE_LINE) {
        inputBuffer += c;
      } else {
        inputBuffer = "";
        Serial.println("[SERIAL] ERROR: command too long");
      }
    }
  }
}

bool isSerialConsoleManualControlActive() {
  if (allWindowsStopped) {
    serialManualControlActive = false;
    return false;
  }

  if (!serialManualControlActive) return false;

  unsigned long now = millis();
  unsigned long overrideMs = WDT_TIMEOUT_MS + 1000UL;
  if (now - lastSerialManualCommandAt > overrideMs) {
    serialManualControlActive = false;
    Serial.println("[SERIAL] manual network override expired");
    return false;
  }

  return true;
}