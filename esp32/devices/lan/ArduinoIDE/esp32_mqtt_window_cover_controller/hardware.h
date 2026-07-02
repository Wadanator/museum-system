#ifndef HARDWARE_H
#define HARDWARE_H

#include <Arduino.h>

enum CoverDirection : uint8_t {
  COVER_DIR_STOPPED = 0,
  COVER_DIR_OPENING = 1,
  COVER_DIR_CLOSING = 2
};

enum CoverState : uint8_t {
  COVER_STATE_UNKNOWN = 0,
  COVER_STATE_OPENING,
  COVER_STATE_CLOSING,
  COVER_STATE_OPEN,
  COVER_STATE_CLOSED,
  COVER_STATE_STOPPED,
  COVER_STATE_ERROR
};

extern bool allCoversStopped;

void initializeHardware();
const char* commandCoverOpen(int coverIndex);
const char* commandCoverClose(int coverIndex);
const char* commandCoverStop(int coverIndex);
void stopAllCovers(const char* source = "safety");
void handleCovers();
String getCoverStatus();
const char* getCoverStateText(int coverIndex);
CoverState getCoverState(int coverIndex);
bool isCoverMoving(int coverIndex);
void markHeartbeatReceived();
bool isHeartbeatHealthy();
bool isHeartbeatRequired();

#endif
