#include "wdt_manager.h"
#include "config.h"
#include "debug.h"
#include <esp_task_wdt.h>

void initializeWatchdog() {
  esp_task_wdt_deinit();

  // Apply the firmware watchdog settings to the current task.
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };

  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  
  debugPrint("[OK] Watchdog timer active (" + String(WDT_TIMEOUT) + "s)");
}

void resetWatchdog() {
  esp_task_wdt_reset();
}
