#include "wdt_manager.h"
#include "config.h"
#include "debug.h"
#include <esp_task_wdt.h>

void initializeWatchdog() {
  esp_task_wdt_deinit();

  // 2. Konfiguracia nasho WDT
  esp_task_wdt_config_t wdt_config = {
    .timeout_ms = WDT_TIMEOUT * 1000,
    .idle_core_mask = 0,
    .trigger_panic = true
  };

  // 3. Inicializacia a pridanie tasku
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
  
  debugPrint("✅ Watchdog Timer aktivny (" + String(WDT_TIMEOUT) + "s)");
}

void resetWatchdog() {
  esp_task_wdt_reset();
}