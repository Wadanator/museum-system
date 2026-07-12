#include "wdt_manager.h"
#include "config.h"
#include "debug.h"
#include <esp_task_wdt.h>

void initializeWatchdog() {
  // Reset the task watchdog service before applying this firmware's settings.
  esp_task_wdt_deinit();

  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT_MS,
    .idle_core_mask = 0,
    .trigger_panic = true
  };

  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  
  debugPrint("[OK] Watchdog timer active (" + String(WDT_TIMEOUT_MS) + "ms)");
}

void resetWatchdog() {
  esp_task_wdt_reset();
}
