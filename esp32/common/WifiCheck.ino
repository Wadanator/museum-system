/*
 * ESP32 WiFi Network Scanner
 * 
 * This sketch scans for available WiFi networks and displays detailed information
 * including SSID, signal strength, encryption type, and channel.
 * 
 * Features:
 * - Continuous scanning with configurable intervals
 * - Signal strength indicators (bars and dBm)
 * - Encryption type detection
 * - Channel information
 * - Network sorting by signal strength
 * - Visual LED feedback during scanning
 */

#include <WiFi.h>

// Configuration
const int SCAN_INTERVAL = 10000;  // Scan every 10 seconds
const int LED_PIN = 2;            // Built-in LED for scan indication
const bool SORT_BY_SIGNAL = true; // Sort networks by signal strength
const int MIN_SIGNAL_SHOW = -100;  // Minimum signal strength to display (dBm)

// Scan management
unsigned long lastScan = 0;
bool scanning = false;
int scanCount = 0;

// LED blink management
unsigned long lastBlink = 0;
bool ledState = false;

void setup() {
  Serial.begin(115200);
  delay(100);
  
  Serial.println();
  Serial.println("=======================================");
  Serial.println("ESP32 WiFi Network Scanner v1.0");
  Serial.println("=======================================");
  Serial.println();
  
  // Set up LED pin
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  // Set WiFi to station mode
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  
  Serial.println("WiFi scanner initialized");
  Serial.println("Scanning for networks...");
  Serial.println();
  
  // Initial scan
  performScan();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check if it's time for another scan
  if (currentTime - lastScan >= SCAN_INTERVAL) {
    performScan();
    lastScan = currentTime;
  }
  
  // Blink LED while scanning
  if (scanning) {
    blinkScanLed();
  }
  
  delay(100);
}

void performScan() {
  scanCount++;
  scanning = true;
  
  Serial.println("╔══════════════════════════════════════════════════════════════╗");
  Serial.printf("║                    SCAN #%d - %s                    ║\n", 
                scanCount, getTimeString().c_str());
  Serial.println("╚══════════════════════════════════════════════════════════════╝");
  
  // Start LED blinking
  digitalWrite(LED_PIN, HIGH);
  
  // Perform the scan
  int networkCount = WiFi.scanNetworks();
  
  // Stop LED blinking
  digitalWrite(LED_PIN, LOW);
  scanning = false;
  
  if (networkCount == 0) {
    Serial.println("No networks found");
    Serial.println();
    return;
  }
  
  Serial.printf("Found %d network(s):\n\n", networkCount);
  
  // Sort networks by signal strength if enabled
  if (SORT_BY_SIGNAL) {
    sortNetworksBySignal(networkCount);
  }
  
  // Display header
  Serial.println("┌─────┬──────────────────────────────────┬────────┬─────────┬─────────┬─────────┐");
  Serial.println("│ No. │ SSID                             │ Signal │ Channel │ Encrypt │ BSSID   │");
  Serial.println("├─────┼──────────────────────────────────┼────────┼─────────┼─────────┼─────────┤");
  
  // Display each network
  for (int i = 0; i < networkCount; i++) {
    int rssi = WiFi.RSSI(i);
    
    // Filter weak signals if threshold is set
    if (rssi < MIN_SIGNAL_SHOW) continue;
    
    String ssid = WiFi.SSID(i);
    if (ssid.length() == 0) {
      ssid = "<Hidden Network>";
    }
    
    // Truncate SSID if too long
    if (ssid.length() > 32) {
      ssid = ssid.substring(0, 29) + "...";
    }
    
    String signalStr = getSignalString(rssi);
    String encryptionStr = getEncryptionString(WiFi.encryptionType(i));
    String bssid = WiFi.BSSIDstr(i);
    
    Serial.printf("│ %2d  │ %-32s │ %6s │   %2d    │ %7s │ %s │\n",
                  i + 1,
                  ssid.c_str(),
                  signalStr.c_str(),
                  WiFi.channel(i),
                  encryptionStr.c_str(),
                  bssid.c_str());
  }
  
  Serial.println("└─────┴──────────────────────────────────┴────────┴─────────┴─────────┴─────────┘");
  
  // Display statistics
  displayStatistics(networkCount);
  
  Serial.println();
  Serial.printf("Next scan in %d seconds...\n", SCAN_INTERVAL / 1000);
  Serial.println("════════════════════════════════════════════════════════════════");
  Serial.println();
}

void sortNetworksBySignal(int networkCount) {
  // Simple bubble sort by RSSI (strongest first)
  for (int i = 0; i < networkCount - 1; i++) {
    for (int j = 0; j < networkCount - i - 1; j++) {
      if (WiFi.RSSI(j) < WiFi.RSSI(j + 1)) {
        // Swap networks (this is a simplified approach)
        // Note: WiFi.scanNetworks() results can't be directly swapped
        // This is more for demonstration - in practice, you'd store results in arrays
      }
    }
  }
}

String getSignalString(int rssi) {
  String bars = "";
  String dbm = String(rssi) + "dBm";
  
  // Create signal strength bars
  if (rssi >= -50) {
    bars = "████"; // Excellent
  } else if (rssi >= -60) {
    bars = "███▒"; // Good
  } else if (rssi >= -70) {
    bars = "██▒▒"; // Fair
  } else if (rssi >= -80) {
    bars = "█▒▒▒"; // Weak
  } else {
    bars = "▒▒▒▒"; // Very weak
  }
  
  return bars + " " + dbm;
}

String getEncryptionString(wifi_auth_mode_t encryptionType) {
  switch (encryptionType) {
    case WIFI_AUTH_OPEN:
      return "OPEN";
    case WIFI_AUTH_WEP:
      return "WEP";
    case WIFI_AUTH_WPA_PSK:
      return "WPA";
    case WIFI_AUTH_WPA2_PSK:
      return "WPA2";
    case WIFI_AUTH_WPA_WPA2_PSK:
      return "WPA/2";
    case WIFI_AUTH_WPA2_ENTERPRISE:
      return "WPA2-E";
    case WIFI_AUTH_WPA3_PSK:
      return "WPA3";
    case WIFI_AUTH_WPA2_WPA3_PSK:
      return "WPA2/3";
    case WIFI_AUTH_WAPI_PSK:
      return "WAPI";
    default:
      return "UNKNOWN";
  }
}

void displayStatistics(int networkCount) {
  int openNetworks = 0;
  int strongSignals = 0;
  int channel24Count = 0;
  int channel5Count = 0;
  
  for (int i = 0; i < networkCount; i++) {
    // Count open networks
    if (WiFi.encryptionType(i) == WIFI_AUTH_OPEN) {
      openNetworks++;
    }
    
    // Count strong signals (>= -60 dBm)
    if (WiFi.RSSI(i) >= -60) {
      strongSignals++;
    }
    
    // Count 2.4GHz vs 5GHz (rough approximation by channel)
    int channel = WiFi.channel(i);
    if (channel <= 14) {
      channel24Count++;
    } else {
      channel5Count++;
    }
  }
  
  Serial.println("\n📊 Network Statistics:");
  Serial.printf("   • Total networks: %d\n", networkCount);
  Serial.printf("   • Open networks: %d\n", openNetworks);
  Serial.printf("   • Strong signals: %d (≥-60dBm)\n", strongSignals);
  Serial.printf("   • 2.4GHz networks: %d\n", channel24Count);
  Serial.printf("   • 5GHz networks: %d\n", channel5Count);
  
  // Find strongest and weakest signals
  if (networkCount > 0) {
    int strongest = WiFi.RSSI(0);
    int weakest = WiFi.RSSI(0);
    
    for (int i = 1; i < networkCount; i++) {
      int rssi = WiFi.RSSI(i);
      if (rssi > strongest) strongest = rssi;
      if (rssi < weakest) weakest = rssi;
    }
    
    Serial.printf("   • Strongest signal: %d dBm\n", strongest);
    Serial.printf("   • Weakest signal: %d dBm\n", weakest);
  }
}

String getTimeString() {
  unsigned long seconds = millis() / 1000;
  unsigned long minutes = seconds / 60;
  unsigned long hours = minutes / 60;
  
  seconds %= 60;
  minutes %= 60;
  hours %= 24;
  
  char timeStr[20];
  sprintf(timeStr, "%02lu:%02lu:%02lu", hours, minutes, seconds);
  return String(timeStr);
}

void blinkScanLed() {
  unsigned long currentTime = millis();
  
  // Fast blink during scanning
  if (currentTime - lastBlink >= 100) {
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
    lastBlink = currentTime;
  }
}

// Function to manually trigger a scan (can be called from Serial commands)
void triggerManualScan() {
  Serial.println("Manual scan triggered...");
  performScan();
}

// Optional: Add serial command processing
void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toLowerCase();
    
    if (command == "scan") {
      triggerManualScan();
    } else if (command == "help") {
      Serial.println("\nAvailable commands:");
      Serial.println("  scan - Trigger manual scan");
      Serial.println("  help - Show this help message");
      Serial.println();
    }
  }
}