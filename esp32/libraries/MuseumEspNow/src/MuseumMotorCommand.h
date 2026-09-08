#pragma once

#include "MuseumEspNow.h"
#include <stdio.h>

namespace museum {

struct MotorCommand {
  char action[6] = {};
  char speed[4] = "0";
  char direction[2] = "S";
  char ramp[11] = "0";
};

inline bool parseDecimal(const char* text, uint32_t maximum, uint32_t& value) {
  if (!text || !*text) return false;
  value = 0;
  for (const char* p = text; *p; ++p) {
    if (*p < '0' || *p > '9') return false;
    const uint32_t digit = uint32_t(*p - '0');
    if (value > maximum / 10 || (value == maximum / 10 && digit > maximum % 10)) return false;
    value = value * 10 + digit;
  }
  return true;
}

inline bool parseDirection(const char* text) {
  return text && text[0] && !text[1] &&
      (text[0] == 'L' || text[0] == 'R' || text[0] == 'l' || text[0] == 'r');
}

inline bool parseMotorCommand(const char* input, uint32_t maxRamp, MotorCommand& out) {
  if (!input || strlen(input) >= PayloadSize) return false;
  char buffer[PayloadSize];
  strcpy(buffer, input);
  char* parts[4] = {buffer, nullptr, nullptr, nullptr};
  size_t count = 1;
  for (char* p = buffer; *p; ++p) {
    if (*p != ':') continue;
    if (count == 4) return false;
    *p = 0; parts[count++] = p + 1;
  }
  MotorCommand cmd;
  uint32_t speed = 0, ramp = 0;
  if (!strcmp(parts[0], "ON")) {
    if ((count != 3 && count != 4) || !parseDecimal(parts[1], 100, speed) || !speed ||
        !parseDirection(parts[2]) || (count == 4 && !parseDecimal(parts[3], maxRamp, ramp)))
      return false;
    cmd.direction[0] = parts[2][0];
  } else if (!strcmp(parts[0], "OFF")) {
    if (count != 1) return false;
  } else if (!strcmp(parts[0], "SPEED")) {
    if (count != 2 || !parseDecimal(parts[1], 100, speed)) return false;
  } else if (!strcmp(parts[0], "DIR")) {
    if (count != 2 || !parseDirection(parts[1])) return false;
    cmd.direction[0] = parts[1][0];
  } else return false;
  strcpy(cmd.action, parts[0]);
  snprintf(cmd.speed, sizeof(cmd.speed), "%u", unsigned(speed));
  snprintf(cmd.ramp, sizeof(cmd.ramp), "%lu", static_cast<unsigned long>(ramp));
  out = cmd;
  return true;
}

}  // namespace museum
