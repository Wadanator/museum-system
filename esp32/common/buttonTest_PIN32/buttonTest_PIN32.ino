// Testovací skript pre overenie zapojenia tlačidla
// Zapojenie: 3.3V -> Rezistor (6k-10k) -> Pin 32 -> Tlačidlo -> GND

const int BUTTON_PIN = 32;

void setup() {
  // Inicializácia sériovej linky
  Serial.begin(115200);
  delay(1000);
  
  // Používame INPUT, pretože máš externý rezistor
  pinMode(BUTTON_PIN, INPUT);
  
  Serial.println("--- Test stability tlacidla ---");
  Serial.println("Ocakavany stav: 1 (uvolnene), 0 (stlacene)");
}

void loop() {
  // Priame citanie stavu pinu bez debouncu a cooldownu
  int stav = digitalRead(BUTTON_PIN);
  
  // Vypis do konzoly
  Serial.print("Stav pinu 32: ");
  Serial.println(stav);

  // Ak uvidis 0, znamena to, ze pin je spojeny so zemou (GND)
  if (stav == LOW) {
    Serial.println(">>> TLACIDLO ZOPNUTE <<<");
  }

  // Kratka pauza, aby sa dal vypis stihat citat
  delay(100); 
}