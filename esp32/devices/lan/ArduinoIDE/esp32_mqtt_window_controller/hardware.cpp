#include "hardware.h"
#include "config.h"
#include "debug.h"
#include "mqtt_manager.h"
#include "pwm_driver.h"

static const int MAX_WINDOW_SIDES = 4;

bool allWindowsStopped = true;

static WindowState windowStates[MAX_WINDOW_SIDES];
static WindowDirection activeDirections[MAX_WINDOW_SIDES];
static WindowDirection pendingDirections[MAX_WINDOW_SIDES];
static unsigned long pendingActivationAt[MAX_WINDOW_SIDES];
static unsigned long moveStartedAt[MAX_WINDOW_SIDES];
static bool closeEndstopPressActive[MAX_WINDOW_SIDES];
static unsigned long closeEndstopPressStartedAt[MAX_WINDOW_SIDES];
static uint8_t runtimeSpeeds[MAX_WINDOW_SIDES];
static uint8_t pendingSpeeds[MAX_WINDOW_SIDES];
static unsigned long lastEndstopPoll = 0;

static bool isValidWindowSideIndex(int sideIndex) {
  return sideIndex >= 0 && sideIndex < WINDOW_SIDE_COUNT && sideIndex < MAX_WINDOW_SIDES;
}

static bool isWindowSideEnabled(int sideIndex) {
  return isValidWindowSideIndex(sideIndex) && WINDOW_SIDES[sideIndex].enabled;
}

static bool isWindowSideConfigSafe(int sideIndex) {
  if (!isWindowSideEnabled(sideIndex)) return false;

  const WindowSideConfig& side = WINDOW_SIDES[sideIndex];
  if (side.topicName == nullptr || side.topicName[0] == '\0') return false;
  if (side.pwmOpenChannel >= PWM_CHANNEL_COUNT ||
      side.pwmCloseChannel >= PWM_CHANNEL_COUNT) {
    return false;
  }
  if (side.pwmOpenChannel == side.pwmCloseChannel) return false;
  if (side.defaultSpeed > 100) return false;
  if (side.maxOpenMoveMs == 0 || side.maxCloseMoveMs == 0) return false;
  if (side.endstopsEnabled && side.openEndstopPin >= 0 &&
      side.openEndstopPin == side.closeEndstopPin) {
    return false;
  }

  for (int otherIndex = 0; otherIndex < WINDOW_SIDE_COUNT && otherIndex < MAX_WINDOW_SIDES; otherIndex++) {
    if (otherIndex == sideIndex || !isWindowSideEnabled(otherIndex)) continue;
    const WindowSideConfig& other = WINDOW_SIDES[otherIndex];
    if (side.pwmOpenChannel == other.pwmOpenChannel ||
        side.pwmOpenChannel == other.pwmCloseChannel ||
        side.pwmCloseChannel == other.pwmOpenChannel ||
        side.pwmCloseChannel == other.pwmCloseChannel) {
      return false;
    }
  }

  return true;
}

static bool parseSpeed(const char* speedValue, uint8_t& speed) {
  if (speedValue == nullptr || speedValue[0] == '\0') return false;

  char* endPtr = nullptr;
  long parsed = strtol(speedValue, &endPtr, 10);
  if (endPtr == speedValue || *endPtr != '\0') return false;

  speed = (uint8_t)constrain((int)parsed, 0, 100);
  return true;
}

static uint16_t dutyFromSpeed(uint8_t speed) {
  uint8_t safeSpeed = (uint8_t)constrain((int)speed, 0, 100);
  return (uint16_t)map(safeSpeed, 0, 100, PWM_DUTY_OFF, PWM_DUTY_MAX);
}

static const char* directionText(WindowDirection direction) {
  switch (direction) {
    case WINDOW_DIR_OPENING: return "OPENING";
    case WINDOW_DIR_CLOSING: return "CLOSING";
    default: return "STOPPED";
  }
}

static unsigned long maxMoveMsForDirection(const WindowSideConfig& side, WindowDirection direction) {
  return direction == WINDOW_DIR_CLOSING ? side.maxCloseMoveMs : side.maxOpenMoveMs;
}

static bool shouldBlockMovementAtTargetEndstop(const WindowSideConfig& side, WindowDirection direction) {
  return direction == WINDOW_DIR_OPENING || side.closeEndstopPressMs == 0;
}

const char* getWindowDirectionText(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return "STOPPED";
  if (activeDirections[sideIndex] != WINDOW_DIR_STOPPED) return directionText(activeDirections[sideIndex]);
  return directionText(pendingDirections[sideIndex]);
}

const char* getWindowStateText(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return "UNKNOWN";

  switch (windowStates[sideIndex]) {
    case WINDOW_STATE_OPENING: return "OPENING";
    case WINDOW_STATE_CLOSING: return "CLOSING";
    case WINDOW_STATE_OPEN: return "OPEN";
    case WINDOW_STATE_CLOSED: return "CLOSED";
    case WINDOW_STATE_STOPPED: return "STOPPED";
    case WINDOW_STATE_ERROR: return "ERROR";
    default: return "UNKNOWN";
  }
}

WindowState getWindowState(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return WINDOW_STATE_UNKNOWN;
  return windowStates[sideIndex];
}

bool isWindowMoving(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return false;
  return activeDirections[sideIndex] != WINDOW_DIR_STOPPED ||
         pendingDirections[sideIndex] != WINDOW_DIR_STOPPED;
}

int getWindowSpeed(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return 0;
  if (activeDirections[sideIndex] != WINDOW_DIR_STOPPED) return runtimeSpeeds[sideIndex];
  if (pendingDirections[sideIndex] != WINDOW_DIR_STOPPED) return pendingSpeeds[sideIndex];
  return 0;
}

static void refreshAllStoppedFlag() {
  bool anyMoving = false;
  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    if (!isWindowSideEnabled(i)) continue;
    if (activeDirections[i] != WINDOW_DIR_STOPPED ||
        pendingDirections[i] != WINDOW_DIR_STOPPED) {
      anyMoving = true;
      break;
    }
  }
  allWindowsStopped = !anyMoving;
}

static bool readConfiguredEndstop(int pin, bool activeLow) {
  if (pin < 0) return false;
  int reading = digitalRead(pin);
  return activeLow ? (reading == LOW) : (reading == HIGH);
}

static bool isOpenEndstopActive(int sideIndex) {
  if (!isWindowSideConfigSafe(sideIndex)) return false;
  const WindowSideConfig& side = WINDOW_SIDES[sideIndex];
  if (!side.endstopsEnabled) return false;
  return readConfiguredEndstop(side.openEndstopPin, side.endstopActiveLow);
}

static bool isCloseEndstopActive(int sideIndex) {
  if (!isWindowSideConfigSafe(sideIndex)) return false;
  const WindowSideConfig& side = WINDOW_SIDES[sideIndex];
  if (!side.endstopsEnabled) return false;
  return readConfiguredEndstop(side.closeEndstopPin, side.endstopActiveLow);
}

static WindowState detectRestingState(int sideIndex) {
  if (!WINDOW_SIDES[sideIndex].endstopsEnabled) return WINDOW_STATE_UNKNOWN;

  bool openStop = isOpenEndstopActive(sideIndex);
  bool closeStop = isCloseEndstopActive(sideIndex);

  if (openStop && !closeStop) return WINDOW_STATE_OPEN;
  if (closeStop && !openStop) return WINDOW_STATE_CLOSED;
  if (openStop && closeStop) return WINDOW_STATE_ERROR;
  return WINDOW_STATE_UNKNOWN;
}

static void configureEndstops() {
  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    if (!isWindowSideEnabled(i)) continue;
    if (!isWindowSideConfigSafe(i)) {
      debugPrint(String(WINDOW_SIDES[i].topicName) + " has unsafe configuration");
      continue;
    }

    const WindowSideConfig& side = WINDOW_SIDES[i];
    if (!side.endstopsEnabled) continue;
    if (side.openEndstopPin >= 0) pinMode(side.openEndstopPin, ENDSTOP_INPUT_MODE);
    if (side.closeEndstopPin >= 0) pinMode(side.closeEndstopPin, ENDSTOP_INPUT_MODE);
  }
}

static void clearPendingWindowStart(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return;
  pendingDirections[sideIndex] = WINDOW_DIR_STOPPED;
  pendingActivationAt[sideIndex] = 0;
  pendingSpeeds[sideIndex] = 0;
}

static void clearCloseEndstopPress(int sideIndex) {
  if (!isValidWindowSideIndex(sideIndex)) return;
  closeEndstopPressActive[sideIndex] = false;
  closeEndstopPressStartedAt[sideIndex] = 0;
}

static PwmResult stopWindowHardware(int sideIndex) {
  if (!isWindowSideConfigSafe(sideIndex)) return PWM_RESULT_INVALID_CHANNEL;

  const WindowSideConfig& side = WINDOW_SIDES[sideIndex];
  PwmResult openResult = writePwmChannel(side.pwmOpenChannel, PWM_DUTY_OFF);
  PwmResult closeResult = writePwmChannel(side.pwmCloseChannel, PWM_DUTY_OFF);

  if (openResult == PWM_RESULT_OK && closeResult == PWM_RESULT_OK) {
    activeDirections[sideIndex] = WINDOW_DIR_STOPPED;
    clearPendingWindowStart(sideIndex);
    clearCloseEndstopPress(sideIndex);
    moveStartedAt[sideIndex] = 0;
    refreshAllStoppedFlag();
    return PWM_RESULT_OK;
  }

  windowStates[sideIndex] = WINDOW_STATE_ERROR;
  refreshAllStoppedFlag();
  return openResult != PWM_RESULT_OK ? openResult : closeResult;
}

static PwmResult writeActiveWindowSpeed(int sideIndex, uint8_t speed) {
  if (!isWindowSideConfigSafe(sideIndex)) return PWM_RESULT_INVALID_CHANNEL;
  if (activeDirections[sideIndex] == WINDOW_DIR_STOPPED) return PWM_RESULT_OK;

  const WindowSideConfig& side = WINDOW_SIDES[sideIndex];
  uint8_t activeChannel = activeDirections[sideIndex] == WINDOW_DIR_OPENING
    ? side.pwmOpenChannel
    : side.pwmCloseChannel;

  return writePwmChannel(activeChannel, dutyFromSpeed(speed));
}

static PwmResult startWindowHardware(int sideIndex, WindowDirection direction, uint8_t speed) {
  if (!isWindowSideConfigSafe(sideIndex)) return PWM_RESULT_INVALID_CHANNEL;
  if (speed == 0) return PWM_RESULT_INVALID_DUTY;

  const WindowSideConfig& side = WINDOW_SIDES[sideIndex];
  uint8_t oppositeChannel = direction == WINDOW_DIR_OPENING ? side.pwmCloseChannel : side.pwmOpenChannel;

  // Firmware-level mutual exclusion: the opposite direction is forced to zero
  // first. The requested direction is enabled later by handleWindows() after
  // the configured dead-time, so MQTT handling and the main loop stay responsive.
  PwmResult result = writePwmChannel(oppositeChannel, PWM_DUTY_OFF);
  if (result != PWM_RESULT_OK) return result;

  clearCloseEndstopPress(sideIndex);
  pendingDirections[sideIndex] = direction;
  pendingSpeeds[sideIndex] = speed;
  pendingActivationAt[sideIndex] = millis() + DIRECTION_CHANGE_DEADTIME_MS;
  windowStates[sideIndex] = direction == WINDOW_DIR_OPENING ? WINDOW_STATE_OPENING : WINDOW_STATE_CLOSING;
  refreshAllStoppedFlag();
  return PWM_RESULT_OK;
}

static void processPendingWindowStarts(unsigned long currentTime) {
  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    if (!isWindowSideEnabled(i)) continue;
    if (pendingDirections[i] == WINDOW_DIR_STOPPED) continue;
    if ((long)(currentTime - pendingActivationAt[i]) < 0) continue;

    WindowDirection direction = pendingDirections[i];
    uint8_t speed = pendingSpeeds[i];
    const WindowSideConfig& side = WINDOW_SIDES[i];
    bool opening = direction == WINDOW_DIR_OPENING;

    bool targetEndstopActive = opening ? isOpenEndstopActive(i) : isCloseEndstopActive(i);
    if (targetEndstopActive && shouldBlockMovementAtTargetEndstop(side, direction)) {
      clearPendingWindowStart(i);
      windowStates[i] = opening ? WINDOW_STATE_OPEN : WINDOW_STATE_CLOSED;
      refreshAllStoppedFlag();
      publishWindowState(i, "endstop", true);
      publishWindowFeedback(i, "ERROR:ENDSTOP");
      continue;
    }

    uint8_t activeChannel = opening ? side.pwmOpenChannel : side.pwmCloseChannel;
    PwmResult result = writePwmChannel(activeChannel, dutyFromSpeed(speed));
    if (result != PWM_RESULT_OK) {
      clearPendingWindowStart(i);
      windowStates[i] = WINDOW_STATE_ERROR;
      refreshAllStoppedFlag();
      publishWindowState(i, "hardware_error", true);
      publishWindowFeedback(i, pwmResultText(result));
      continue;
    }

    activeDirections[i] = direction;
    runtimeSpeeds[i] = speed;
    moveStartedAt[i] = currentTime;
    clearPendingWindowStart(i);
    refreshAllStoppedFlag();
    debugPrint(String(WINDOW_SIDES[i].topicName) + " -> " + directionText(direction) + " active @ " + String(speed) + "%");
    publishWindowState(i, "deadtime_complete", true);
  }
}

void initializeHardware() {
  debugPrint("Initializing window hardware...");

  initializePwmDriver();
  configureEndstops();
  PwmResult frequencyResult = configureAllPwmFrequencies();
  if (frequencyResult != PWM_RESULT_OK) {
    debugPrint("PWM frequency setup failed: " + String(pwmResultText(frequencyResult)));
  }

  PwmResult offResult = writeAllPwmChannelsOff();
  if (offResult != PWM_RESULT_OK) {
    debugPrint("PWM startup safe-off failed: " + String(pwmResultText(offResult)));
  }

  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    activeDirections[i] = WINDOW_DIR_STOPPED;
    pendingDirections[i] = WINDOW_DIR_STOPPED;
    pendingActivationAt[i] = 0;
    moveStartedAt[i] = 0;
    closeEndstopPressActive[i] = false;
    closeEndstopPressStartedAt[i] = 0;
    runtimeSpeeds[i] = isWindowSideEnabled(i) ? WINDOW_SIDES[i].defaultSpeed : 0;
    pendingSpeeds[i] = 0;

    if (!isWindowSideEnabled(i)) {
      windowStates[i] = WINDOW_STATE_UNKNOWN;
      debugPrint(String(WINDOW_SIDES[i].topicName) + " disabled");
      continue;
    }

    windowStates[i] = isWindowSideConfigSafe(i) ? detectRestingState(i) : WINDOW_STATE_ERROR;
    debugPrint(String(WINDOW_SIDES[i].topicName) + " initial state: " + getWindowStateText(i));
  }

  allWindowsStopped = true;
  debugPrint("Window hardware initialized - all PWM channels OFF");
}

static const char* startWindowMovement(int sideIndex, WindowDirection direction, const char* speedValue) {
  if (!isWindowSideConfigSafe(sideIndex)) return "ERROR:CONFIG";

  uint8_t speed = runtimeSpeeds[sideIndex] > 0
    ? runtimeSpeeds[sideIndex]
    : WINDOW_SIDES[sideIndex].defaultSpeed;
  if (pendingDirections[sideIndex] != WINDOW_DIR_STOPPED && pendingSpeeds[sideIndex] > 0) {
    speed = pendingSpeeds[sideIndex];
  }
  if (speedValue != nullptr && speedValue[0] != '\0' && !parseSpeed(speedValue, speed)) {
    return "ERROR:INVALID_SPEED";
  }
  if (speed == 0) return "ERROR:INVALID_SPEED";

  bool opening = direction == WINDOW_DIR_OPENING;
  bool targetEndstop = opening ? isOpenEndstopActive(sideIndex) : isCloseEndstopActive(sideIndex);
  if (targetEndstop && shouldBlockMovementAtTargetEndstop(WINDOW_SIDES[sideIndex], direction)) {
    PwmResult stopResult = stopWindowHardware(sideIndex);
    windowStates[sideIndex] = opening ? WINDOW_STATE_OPEN : WINDOW_STATE_CLOSED;
    publishWindowState(sideIndex, "endstop", true);
    return stopResult == PWM_RESULT_OK ? "ERROR:ENDSTOP" : pwmResultText(stopResult);
  }

  if (pendingDirections[sideIndex] == direction) {
    pendingSpeeds[sideIndex] = speed;
    runtimeSpeeds[sideIndex] = speed;
    publishWindowState(sideIndex, "command", true);
    return "OK";
  }

  if (pendingDirections[sideIndex] != WINDOW_DIR_STOPPED &&
      pendingDirections[sideIndex] != direction) {
    PwmResult stopResult = stopWindowHardware(sideIndex);
    if (stopResult != PWM_RESULT_OK) {
      publishWindowState(sideIndex, "hardware_error", true);
      return pwmResultText(stopResult);
    }
  }

  if (activeDirections[sideIndex] == direction) {
    runtimeSpeeds[sideIndex] = speed;
    PwmResult result = writeActiveWindowSpeed(sideIndex, speed);
    if (result != PWM_RESULT_OK) {
      windowStates[sideIndex] = WINDOW_STATE_ERROR;
      publishWindowState(sideIndex, "hardware_error", true);
      return pwmResultText(result);
    }

    // Same-direction commands update speed only. They intentionally do not
    // reset moveStartedAt[], so direction max movement time is a continuous-run limit.
    publishWindowState(sideIndex, "command", true);
    return "OK";
  }

  if (activeDirections[sideIndex] != WINDOW_DIR_STOPPED &&
      activeDirections[sideIndex] != direction) {
    PwmResult stopResult = stopWindowHardware(sideIndex);
    if (stopResult != PWM_RESULT_OK) {
      publishWindowState(sideIndex, "hardware_error", true);
      return pwmResultText(stopResult);
    }
  }

  PwmResult result = startWindowHardware(sideIndex, direction, speed);
  if (result != PWM_RESULT_OK) {
    windowStates[sideIndex] = WINDOW_STATE_ERROR;
    publishWindowState(sideIndex, "hardware_error", true);
    return pwmResultText(result);
  }

  debugPrint(String(WINDOW_SIDES[sideIndex].topicName) + " -> " + directionText(direction) + " scheduled @ " + String(speed) + "%");
  publishWindowState(sideIndex, "command", true);
  return "OK";
}

const char* commandWindowOpen(int sideIndex, const char* speedValue) {
  return startWindowMovement(sideIndex, WINDOW_DIR_OPENING, speedValue);
}

const char* commandWindowClose(int sideIndex, const char* speedValue) {
  return startWindowMovement(sideIndex, WINDOW_DIR_CLOSING, speedValue);
}

const char* commandWindowStop(int sideIndex) {
  if (!isWindowSideConfigSafe(sideIndex)) return "ERROR:CONFIG";

  PwmResult result = stopWindowHardware(sideIndex);
  if (result == PWM_RESULT_OK) {
    windowStates[sideIndex] = WINDOW_STATE_STOPPED;
  } else {
    windowStates[sideIndex] = WINDOW_STATE_ERROR;
  }

  publishWindowState(sideIndex, "command", true);
  return pwmResultText(result);
}

const char* commandWindowSpeed(int sideIndex, const char* speedValue) {
  if (!isWindowSideConfigSafe(sideIndex)) return "ERROR:CONFIG";

  uint8_t speed = 0;
  if (!parseSpeed(speedValue, speed)) return "ERROR:INVALID_SPEED";

  runtimeSpeeds[sideIndex] = speed;
  if (pendingDirections[sideIndex] != WINDOW_DIR_STOPPED) {
    pendingSpeeds[sideIndex] = speed;
  }
  if (speed == 0) {
    return commandWindowStop(sideIndex);
  }

  PwmResult result = writeActiveWindowSpeed(sideIndex, speed);
  if (result != PWM_RESULT_OK) {
    windowStates[sideIndex] = WINDOW_STATE_ERROR;
    publishWindowState(sideIndex, "hardware_error", true);
    return pwmResultText(result);
  }

  publishWindowState(sideIndex, "speed", true);
  return "OK";
}

void stopAllWindows(const char* source) {
  debugPrint("Stopping all windows: " + String(source));

  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    if (!isWindowSideEnabled(i)) continue;
    PwmResult result = stopWindowHardware(i);
    if (result == PWM_RESULT_OK) {
      if (windowStates[i] == WINDOW_STATE_OPENING || windowStates[i] == WINDOW_STATE_CLOSING) {
        windowStates[i] = WINDOW_STATE_STOPPED;
      }
    } else {
      windowStates[i] = WINDOW_STATE_ERROR;
      publishWindowFeedback(i, pwmResultText(result));
    }
    publishWindowState(i, source, true);
  }

  refreshAllStoppedFlag();
}

void handleWindows() {
  unsigned long currentTime = millis();

  processPendingWindowStarts(currentTime);

  if (currentTime - lastEndstopPoll < ENDSTOP_POLL_INTERVAL_MS) return;
  lastEndstopPoll = currentTime;

  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    if (!isWindowSideEnabled(i)) continue;
    if (activeDirections[i] == WINDOW_DIR_STOPPED) continue;

    bool reachedOpen = activeDirections[i] == WINDOW_DIR_OPENING && isOpenEndstopActive(i);
    bool reachedClosed = activeDirections[i] == WINDOW_DIR_CLOSING && isCloseEndstopActive(i);

    if (closeEndstopPressActive[i]) {
      if (currentTime - closeEndstopPressStartedAt[i] < WINDOW_SIDES[i].closeEndstopPressMs) {
        continue;
      }

      PwmResult result = stopWindowHardware(i);
      if (result == PWM_RESULT_OK) {
        windowStates[i] = WINDOW_STATE_CLOSED;
        debugPrint(String(WINDOW_SIDES[i].topicName) + " close end-stop press complete -> CLOSED");
        publishWindowFeedback(i, "OK");
      } else {
        windowStates[i] = WINDOW_STATE_ERROR;
        publishWindowFeedback(i, pwmResultText(result));
      }
      publishWindowState(i, "close_endstop_press", true);
      continue;
    }

    if (reachedOpen) {
      PwmResult result = stopWindowHardware(i);
      if (result == PWM_RESULT_OK) {
        windowStates[i] = WINDOW_STATE_OPEN;
        debugPrint(String(WINDOW_SIDES[i].topicName) + " reached end-stop -> " + getWindowStateText(i));
        publishWindowFeedback(i, "OK");
      } else {
        windowStates[i] = WINDOW_STATE_ERROR;
        publishWindowFeedback(i, pwmResultText(result));
      }
      publishWindowState(i, "endstop", true);
      continue;
    }

    if (reachedClosed) {
      if (WINDOW_SIDES[i].closeEndstopPressMs > 0) {
        closeEndstopPressActive[i] = true;
        closeEndstopPressStartedAt[i] = currentTime;
        debugPrint(
          String(WINDOW_SIDES[i].topicName) +
          " reached CLOSE end-stop -> pressing for " +
          String(WINDOW_SIDES[i].closeEndstopPressMs) +
          "ms"
        );
        publishWindowState(i, "close_endstop_press", true);
        continue;
      }

      PwmResult result = stopWindowHardware(i);
      if (result == PWM_RESULT_OK) {
        windowStates[i] = WINDOW_STATE_CLOSED;
        debugPrint(String(WINDOW_SIDES[i].topicName) + " reached end-stop -> " + getWindowStateText(i));
        publishWindowFeedback(i, "OK");
      } else {
        windowStates[i] = WINDOW_STATE_ERROR;
        publishWindowFeedback(i, pwmResultText(result));
      }
      publishWindowState(i, "endstop", true);
      continue;
    }

    unsigned long maxMoveMs = maxMoveMsForDirection(WINDOW_SIDES[i], activeDirections[i]);
    if (maxMoveMs > 0 && currentTime - moveStartedAt[i] >= maxMoveMs) {
      PwmResult result = stopWindowHardware(i);
      windowStates[i] = result == PWM_RESULT_OK ? WINDOW_STATE_STOPPED : WINDOW_STATE_ERROR;
      debugPrint(String(WINDOW_SIDES[i].topicName) + " move timeout");
      publishWindowState(i, "timeout", true);
      publishWindowFeedback(i, result == PWM_RESULT_OK ? "ERROR:TIMEOUT" : pwmResultText(result));
    }
  }
}

String getWindowStatus() {
  String status = "";
  bool first = true;
  for (int i = 0; i < WINDOW_SIDE_COUNT && i < MAX_WINDOW_SIDES; i++) {
    if (!isWindowSideEnabled(i)) continue;
    if (!first) status += ",";
    status += String(WINDOW_SIDES[i].topicName) + ":" + getWindowStateText(i);
    first = false;
  }
  return status;
}
