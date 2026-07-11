#include "hardware.h"
#include "config.h"
#include "debug.h"
#include "mqtt_manager.h"
#include "pwm_driver.h"

static const int MAX_COVERS = 4;

bool allCoversStopped = true;

static CoverState coverStates[MAX_COVERS];
static CoverDirection activeDirections[MAX_COVERS];
static unsigned long moveStartedAt[MAX_COVERS];
static unsigned long lastEndstopPoll = 0;
static unsigned long lastHeartbeatTime = 0;
static bool heartbeatFailSafeLatched = false;

static bool isValidCoverIndex(int coverIndex) {
  return coverIndex >= 0 && coverIndex < COVER_COUNT && coverIndex < MAX_COVERS;
}

static bool isCoverEnabled(int coverIndex) {
  return isValidCoverIndex(coverIndex) && COVERS[coverIndex].enabled;
}

static bool isCoverConfigSafe(int coverIndex) {
  if (!isCoverEnabled(coverIndex)) return false;

  const CoverConfig& cover = COVERS[coverIndex];
  if (cover.pwmOpenChannel >= PWM_CHANNEL_COUNT ||
      cover.pwmCloseChannel >= PWM_CHANNEL_COUNT) {
    return false;
  }
  if (cover.pwmOpenChannel == cover.pwmCloseChannel) return false;
  if (cover.pwmDuty > PWM_DUTY_MAX) return false;
  if (cover.openEndstopPin >= 0 &&
      cover.openEndstopPin == cover.closeEndstopPin) {
    return false;
  }

  return true;
}

static const char* directionText(CoverDirection direction) {
  switch (direction) {
    case COVER_DIR_OPENING: return "OPENING";
    case COVER_DIR_CLOSING: return "CLOSING";
    default: return "STOPPED";
  }
}

const char* getCoverStateText(int coverIndex) {
  if (!isValidCoverIndex(coverIndex)) return "UNKNOWN";

  switch (coverStates[coverIndex]) {
    case COVER_STATE_OPENING: return "OPENING";
    case COVER_STATE_CLOSING: return "CLOSING";
    case COVER_STATE_OPEN: return "OPEN";
    case COVER_STATE_CLOSED: return "CLOSED";
    case COVER_STATE_STOPPED: return "STOPPED";
    case COVER_STATE_ERROR: return "ERROR";
    default: return "UNKNOWN";
  }
}

CoverState getCoverState(int coverIndex) {
  if (!isValidCoverIndex(coverIndex)) return COVER_STATE_UNKNOWN;
  return coverStates[coverIndex];
}

bool isCoverMoving(int coverIndex) {
  if (!isValidCoverIndex(coverIndex)) return false;
  return activeDirections[coverIndex] != COVER_DIR_STOPPED;
}

bool isHeartbeatRequired() {
  return HEARTBEAT_TIMEOUT_MS > 0;
}

void markHeartbeatReceived() {
  lastHeartbeatTime = millis();
  heartbeatFailSafeLatched = false;
}

bool isHeartbeatHealthy() {
  if (!isHeartbeatRequired()) return true;
  return millis() - lastHeartbeatTime <= HEARTBEAT_TIMEOUT_MS;
}

static void refreshAllStoppedFlag() {
  bool anyMoving = false;
  for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
    if (!isCoverEnabled(i)) continue;
    if (activeDirections[i] != COVER_DIR_STOPPED) {
      anyMoving = true;
      break;
    }
  }
  allCoversStopped = !anyMoving;
}

static bool readConfiguredEndstop(int pin, bool activeLow) {
  if (pin < 0) return false;
  int reading = digitalRead(pin);
  return activeLow ? (reading == LOW) : (reading == HIGH);
}

static bool isOpenEndstopActive(int coverIndex) {
  if (!isCoverConfigSafe(coverIndex)) return false;
  const CoverConfig& cover = COVERS[coverIndex];
  return readConfiguredEndstop(cover.openEndstopPin, cover.endstopActiveLow);
}

static bool isCloseEndstopActive(int coverIndex) {
  if (!isCoverConfigSafe(coverIndex)) return false;
  const CoverConfig& cover = COVERS[coverIndex];
  return readConfiguredEndstop(cover.closeEndstopPin, cover.endstopActiveLow);
}

static CoverState detectRestingState(int coverIndex) {
  bool openStop = isOpenEndstopActive(coverIndex);
  bool closeStop = isCloseEndstopActive(coverIndex);

  if (openStop && !closeStop) return COVER_STATE_OPEN;
  if (closeStop && !openStop) return COVER_STATE_CLOSED;
  if (openStop && closeStop) return COVER_STATE_ERROR;
  return COVER_STATE_UNKNOWN;
}

static void configureEndstops() {
  for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
    if (!isCoverEnabled(i)) continue;
    if (!isCoverConfigSafe(i)) {
      debugPrint(String(COVERS[i].topicName) + " has unsafe configuration");
      continue;
    }

    const CoverConfig& cover = COVERS[i];
    if (cover.openEndstopPin >= 0) pinMode(cover.openEndstopPin, ENDSTOP_INPUT_MODE);
    if (cover.closeEndstopPin >= 0) pinMode(cover.closeEndstopPin, ENDSTOP_INPUT_MODE);
  }
}

static PwmResult stopCoverHardware(int coverIndex) {
  if (!isCoverConfigSafe(coverIndex)) return PWM_RESULT_INVALID_CHANNEL;

  const CoverConfig& cover = COVERS[coverIndex];
  PwmResult openResult = writePwmChannel(cover.pwmOpenChannel, PWM_DUTY_OFF);
  PwmResult closeResult = writePwmChannel(cover.pwmCloseChannel, PWM_DUTY_OFF);

  if (openResult == PWM_RESULT_OK && closeResult == PWM_RESULT_OK) {
    activeDirections[coverIndex] = COVER_DIR_STOPPED;
    moveStartedAt[coverIndex] = 0;
    refreshAllStoppedFlag();
    return PWM_RESULT_OK;
  }

  coverStates[coverIndex] = COVER_STATE_ERROR;
  refreshAllStoppedFlag();
  return openResult != PWM_RESULT_OK ? openResult : closeResult;
}

static PwmResult startCoverHardware(int coverIndex, CoverDirection direction) {
  if (!isCoverConfigSafe(coverIndex)) return PWM_RESULT_INVALID_CHANNEL;

  const CoverConfig& cover = COVERS[coverIndex];
  uint8_t activeChannel = direction == COVER_DIR_OPENING ? cover.pwmOpenChannel : cover.pwmCloseChannel;
  uint8_t oppositeChannel = direction == COVER_DIR_OPENING ? cover.pwmCloseChannel : cover.pwmOpenChannel;

  // Firmware-level mutual exclusion: the opposite direction is always forced
  // to zero before the requested direction can receive non-zero duty.
  PwmResult result = writePwmChannel(oppositeChannel, PWM_DUTY_OFF);
  if (result != PWM_RESULT_OK) return result;

  delay(DIRECTION_CHANGE_DEADTIME_MS);

  result = writePwmChannel(activeChannel, cover.pwmDuty);
  if (result != PWM_RESULT_OK) {
    writePwmChannel(activeChannel, PWM_DUTY_OFF);
    return result;
  }

  activeDirections[coverIndex] = direction;
  moveStartedAt[coverIndex] = millis();
  coverStates[coverIndex] = direction == COVER_DIR_OPENING ? COVER_STATE_OPENING : COVER_STATE_CLOSING;
  refreshAllStoppedFlag();
  return PWM_RESULT_OK;
}

void initializeHardware() {
  debugPrint("Initializing window cover hardware...");

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

  for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
    activeDirections[i] = COVER_DIR_STOPPED;
    moveStartedAt[i] = 0;

    if (!isCoverEnabled(i)) {
      coverStates[i] = COVER_STATE_UNKNOWN;
      debugPrint(String(COVERS[i].topicName) + " disabled");
      continue;
    }

    coverStates[i] = isCoverConfigSafe(i) ? detectRestingState(i) : COVER_STATE_ERROR;
    debugPrint(String(COVERS[i].topicName) + " initial state: " + getCoverStateText(i));
  }

  allCoversStopped = true;
  lastHeartbeatTime = millis();
  debugPrint("Window cover hardware initialized - all PWM channels OFF");
}

static const char* startCoverMovement(int coverIndex, CoverDirection direction) {
  if (!isCoverConfigSafe(coverIndex)) return "ERROR:CONFIG";
  if (!isHeartbeatHealthy()) return "ERROR:HEARTBEAT";

  bool opening = direction == COVER_DIR_OPENING;
  bool targetEndstop = opening ? isOpenEndstopActive(coverIndex) : isCloseEndstopActive(coverIndex);
  if (targetEndstop) {
    PwmResult stopResult = stopCoverHardware(coverIndex);
    coverStates[coverIndex] = opening ? COVER_STATE_OPEN : COVER_STATE_CLOSED;
    publishCoverState(coverIndex, "endstop", true);
    return stopResult == PWM_RESULT_OK ? "ERROR:ENDSTOP" : pwmResultText(stopResult);
  }

  if (activeDirections[coverIndex] != COVER_DIR_STOPPED &&
      activeDirections[coverIndex] != direction) {
    PwmResult stopResult = stopCoverHardware(coverIndex);
    if (stopResult != PWM_RESULT_OK) {
      publishCoverState(coverIndex, "hardware_error", true);
      return pwmResultText(stopResult);
    }
  }

  PwmResult result = startCoverHardware(coverIndex, direction);
  if (result != PWM_RESULT_OK) {
    coverStates[coverIndex] = COVER_STATE_ERROR;
    publishCoverState(coverIndex, "hardware_error", true);
    return pwmResultText(result);
  }

  debugPrint(String(COVERS[coverIndex].topicName) + " -> " + directionText(direction));
  publishCoverState(coverIndex, "command", true);
  return "OK";
}

const char* commandCoverOpen(int coverIndex) {
  return startCoverMovement(coverIndex, COVER_DIR_OPENING);
}

const char* commandCoverClose(int coverIndex) {
  return startCoverMovement(coverIndex, COVER_DIR_CLOSING);
}

const char* commandCoverStop(int coverIndex) {
  if (!isCoverConfigSafe(coverIndex)) return "ERROR:CONFIG";

  PwmResult result = stopCoverHardware(coverIndex);
  if (result == PWM_RESULT_OK) {
    coverStates[coverIndex] = COVER_STATE_STOPPED;
  } else {
    coverStates[coverIndex] = COVER_STATE_ERROR;
  }

  publishCoverState(coverIndex, "command", true);
  return pwmResultText(result);
}

void stopAllCovers(const char* source) {
  debugPrint("Stopping all covers: " + String(source));

  for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
    if (!isCoverEnabled(i)) continue;
    PwmResult result = stopCoverHardware(i);
    if (result == PWM_RESULT_OK) {
      if (coverStates[i] == COVER_STATE_OPENING || coverStates[i] == COVER_STATE_CLOSING) {
        coverStates[i] = COVER_STATE_STOPPED;
      }
    } else {
      coverStates[i] = COVER_STATE_ERROR;
      publishCoverFeedback(i, pwmResultText(result));
    }
    publishCoverState(i, source, true);
  }

  refreshAllStoppedFlag();
}

void handleCovers() {
  unsigned long currentTime = millis();

  if (!isHeartbeatHealthy()) {
    if (!allCoversStopped) {
      stopAllCovers("heartbeat_timeout");
      if (!heartbeatFailSafeLatched) {
        for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
          if (isCoverEnabled(i)) publishCoverFeedback(i, "ERROR:HEARTBEAT_TIMEOUT");
        }
      }
    }
    heartbeatFailSafeLatched = true;
    return;
  }

  if (currentTime - lastEndstopPoll < ENDSTOP_POLL_INTERVAL_MS) return;
  lastEndstopPoll = currentTime;

  for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
    if (!isCoverEnabled(i)) continue;
    if (activeDirections[i] == COVER_DIR_STOPPED) continue;

    bool reachedOpen = activeDirections[i] == COVER_DIR_OPENING && isOpenEndstopActive(i);
    bool reachedClosed = activeDirections[i] == COVER_DIR_CLOSING && isCloseEndstopActive(i);

    if (reachedOpen || reachedClosed) {
      PwmResult result = stopCoverHardware(i);
      if (result == PWM_RESULT_OK) {
        coverStates[i] = reachedOpen ? COVER_STATE_OPEN : COVER_STATE_CLOSED;
        debugPrint(String(COVERS[i].topicName) + " reached end-stop -> " + getCoverStateText(i));
        publishCoverFeedback(i, "OK");
      } else {
        coverStates[i] = COVER_STATE_ERROR;
        publishCoverFeedback(i, pwmResultText(result));
      }
      publishCoverState(i, "endstop", true);
      continue;
    }

    if (COVERS[i].maxMoveMs > 0 && currentTime - moveStartedAt[i] >= COVERS[i].maxMoveMs) {
      PwmResult result = stopCoverHardware(i);
      coverStates[i] = result == PWM_RESULT_OK ? COVER_STATE_STOPPED : COVER_STATE_ERROR;
      debugPrint(String(COVERS[i].topicName) + " move timeout");
      publishCoverState(i, "timeout", true);
      publishCoverFeedback(i, result == PWM_RESULT_OK ? "ERROR:TIMEOUT" : pwmResultText(result));
    }
  }
}

String getCoverStatus() {
  String status = "";
  bool first = true;
  for (int i = 0; i < COVER_COUNT && i < MAX_COVERS; i++) {
    if (!isCoverEnabled(i)) continue;
    if (!first) status += ",";
    status += String(COVERS[i].topicName) + ":" + getCoverStateText(i);
    first = false;
  }
  return status;
}
