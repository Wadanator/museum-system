#pragma once

#include <MuseumEspNow.h>

bool executeMotorCommand(museum::Target target, const char* command);
museum::Snapshot readMotorSnapshot();
extern unsigned long lastCommandTime;
