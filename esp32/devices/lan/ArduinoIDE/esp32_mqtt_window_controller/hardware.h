#pragma once

#include <Arduino.h>

enum WindowDirection : uint8_t {
  WINDOW_DIR_STOPPED = 0,
  WINDOW_DIR_OPENING = 1,
  WINDOW_DIR_CLOSING = 2
};

enum WindowState : uint8_t {
  WINDOW_STATE_UNKNOWN = 0,
  WINDOW_STATE_OPENING,
  WINDOW_STATE_CLOSING,
  WINDOW_STATE_OPEN,
  WINDOW_STATE_CLOSED,
  WINDOW_STATE_STOPPED,
  WINDOW_STATE_ERROR
};

extern bool allWindowsStopped;

void initializeHardware();
const char* commandWindowOpen(int sideIndex, const char* speedValue = nullptr);
const char* commandWindowClose(int sideIndex, const char* speedValue = nullptr);
const char* commandWindowStop(int sideIndex);
const char* commandWindowSpeed(int sideIndex, const char* speedValue);
void stopAllWindows(const char* source = "safety");
void handleWindows();
String getWindowStatus();
const char* getWindowStateText(int sideIndex);
WindowState getWindowState(int sideIndex);
bool isWindowMoving(int sideIndex);
int getWindowSpeed(int sideIndex);
const char* getWindowDirectionText(int sideIndex);

