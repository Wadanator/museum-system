#include <WiFi.h>

const char* WIFI_SSID     = "kastielhome";
const char* WIFI_PASSWORD = "Kastiel18";
const uint8_t EXPECTED_CHANNEL = 6;

void setup() {
  Serial.begin(115200);
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Pripajam sa na ");
  Serial.print(WIFI_SSID);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    if (millis() - start > 15000) {
      Serial.println("\nCasovy limit pripojenia vyprsal.");
      return;  // tu nastupi fallback logika (retry / signal pre motory)
    }
  }

  Serial.println("\nPripojene.");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  uint8_t ch = WiFi.channel();
  Serial.printf("Kanal: %d\n", ch);

  if (ch != EXPECTED_CHANNEL) {
    Serial.println("POZOR: kanal routra sa nezhoduje s ocakavanym kanalom ESP-NOW uzlov!");
    // tu mozes napr. odmietnut prepnut fallback rezim a nechat motory na LAN vetve
  }
}

void loop() {}