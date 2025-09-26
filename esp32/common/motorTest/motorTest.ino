// Motor PWM Control s 20kHz a Smooth operáciami - VYLEPŠENÁ VERZIA
// Ovládanie motora cez sériový port s plynulým rozbehom/brzdením
// Príkazy: ON, OFF, L, R, číslo 0-100 pre rýchlosť

// Definície pinov
#define PWM_LEFT_PIN 27    // PWM pin pre ľavý smer
#define PWM_RIGHT_PIN 26   // PWM pin pre pravý smer  
#define ENABLE_PIN 25      // Enable pin pre motor driver

// Nastavenia pre smooth operácie
#define SMOOTH_STEP 2      // Krok zmeny rýchlosti (čím vyšší, tým rýchlejší prechod)
#define SMOOTH_DELAY 20    // Pauza medzi krokmi v ms
#define PWM_FREQUENCY 20000 // 20kHz PWM frekvencia
#define PWM_RESOLUTION 8   // 8-bit rozlíšenie (0-255)

// PWM kanály pre ESP32
#define PWM_LEFT_CHANNEL 0
#define PWM_RIGHT_CHANNEL 1

// Premenné
int motorSpeed = 0;           // Cieľová rýchlosť (0-100)
int currentSpeed = 0;         // Aktuálna rýchlosť PWM (0-100)
char motorDirection = 'S';    // S=Stop, L=Left, R=Right
char currentDirection = 'S';  // Aktuálny smer motora
bool motorEnabled = false;    // Stav motora (ON/OFF)
unsigned long lastUpdate = 0; // Čas posledného smooth update
bool systemReady = false;     // Flag pre inicializáciu systému

void setup() {
  Serial.begin(115200);
  
  // Malé oneskorenie pre stabilizáciu
  delay(100);
  
  Serial.println("=== INICIALIZACIA MOTOR PWM CONTROL ===");
  
  // KRITICKÉ: Najprv nastavíme všetky piny ako výstupy a vypneme ich
  pinMode(PWM_LEFT_PIN, OUTPUT);
  pinMode(PWM_RIGHT_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  
  // Okamžite vypneme všetko
  digitalWrite(PWM_LEFT_PIN, LOW);
  digitalWrite(PWM_RIGHT_PIN, LOW);
  digitalWrite(ENABLE_PIN, LOW);
  
  Serial.println("Piny nastavené a vypnuté");
  
  // Nastavenie PWM frekvencie
  if (!setupPWMFrequency()) {
    Serial.println("CHYBA: Nepodarilo sa nastaviť PWM!");
    while(1) delay(1000); // Zastavíme program
  }
  
  // Úplná inicializácia motora - všetko na nulu
  forceStopMotor();
  
  // Krátka pauza a test PWM
  delay(100);
  testPWMChannels();
  
  systemReady = true;
  
  Serial.println("=== MOTOR PWM CONTROL 20kHz + SMOOTH ===");
  Serial.println("Príkazy:");
  Serial.println("ON  - zapnúť motor");
  Serial.println("OFF - vypnúť motor");
  Serial.println("L   - smer doľava");
  Serial.println("R   - smer doprava");
  Serial.println("0-100 - nastaviť rýchlosť (%)");
  Serial.println("STATUS - zobraziť aktuálny stav");
  Serial.println("========================================");
  printStatus();
}

void loop() {
  // Kontrola inicializácie
  if (!systemReady) {
    delay(100);
    return;
  }
  
  // Spracovanie príkazov
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toUpperCase();
    
    if (input.length() > 0) {
      processCommand(input);
    }
  }
  
  // Smooth update motora
  smoothMotorUpdate();
}

bool setupPWMFrequency() {
  // Nastavenie PWM kanálov pre ESP32
  Serial.print("Nastavujem PWM kanál 0 (ľavý)...");
  if (!ledcAttachPin(PWM_LEFT_PIN, PWM_LEFT_CHANNEL)) {
    Serial.println("CHYBA!");
    return false;
  }
  ledcSetup(PWM_LEFT_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
  Serial.println("OK");
  
  Serial.print("Nastavujem PWM kanál 1 (pravý)...");
  if (!ledcAttachPin(PWM_RIGHT_PIN, PWM_RIGHT_CHANNEL)) {
    Serial.println("CHYBA!");
    return false;
  }
  ledcSetup(PWM_RIGHT_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
  Serial.println("OK");
  
  // Nastavíme PWM na 0
  ledcWrite(PWM_LEFT_CHANNEL, 0);
  ledcWrite(PWM_RIGHT_CHANNEL, 0);
  
  Serial.print("PWM frekvencia nastavená na: ");
  Serial.print(PWM_FREQUENCY);
  Serial.println(" Hz");
  
  return true;
}

void testPWMChannels() {
  Serial.println("Test PWM kanálov...");
  
  // Test ľavého kanála
  ledcWrite(PWM_LEFT_CHANNEL, 50);
  delay(100);
  ledcWrite(PWM_LEFT_CHANNEL, 0);
  
  // Test pravého kanála
  ledcWrite(PWM_RIGHT_CHANNEL, 50);
  delay(100);
  ledcWrite(PWM_RIGHT_CHANNEL, 0);
  
  Serial.println("Test PWM dokončený");
}

void processCommand(String cmd) {
  Serial.print("Príkaz: ");
  Serial.println(cmd);
  
  if (cmd == "ON") {
    motorEnabled = true;
    digitalWrite(ENABLE_PIN, HIGH);
    Serial.println("Motor ZAPNUTÝ");
    
  } else if (cmd == "OFF") {
    motorEnabled = false;
    motorSpeed = 0; // Nastavíme cieľovú rýchlosť na 0 pre plynulé zastavenie
    Serial.println("Motor sa vypína...");
    
  } else if (cmd == "L") {
    if (motorDirection != 'L') {
      motorDirection = 'L';
      Serial.println("Smer: ĽAVO");
    }
    
  } else if (cmd == "R") {
    if (motorDirection != 'R') {
      motorDirection = 'R';
      Serial.println("Smer: PRAVO");
    }
    
  } else if (cmd == "STATUS") {
    printDetailedStatus();
    return;
    
  } else if (isNumeric(cmd)) {
    int speed = cmd.toInt();
    if (speed >= 0 && speed <= 100) {
      motorSpeed = speed;
      Serial.print("Cieľová rýchlosť nastavená na: ");
      Serial.print(motorSpeed);
      Serial.println("%");
      
      // Ak nastavujeme rýchlosť > 0, automaticky zapneme motor
      if (speed > 0 && !motorEnabled) {
        Serial.println("Automaticky zapínam motor...");
        motorEnabled = true;
        digitalWrite(ENABLE_PIN, HIGH);
      }
    } else {
      Serial.println("CHYBA: Rýchlosť musí byť 0-100");
    }
    
  } else {
    Serial.println("CHYBA: Neznámy príkaz");
    Serial.println("Platné príkazy: ON, OFF, L, R, 0-100, STATUS");
  }
  
  printStatus();
}

void smoothMotorUpdate() {
  unsigned long currentTime = millis();
  
  // Kontrola, či je čas na update
  if (currentTime - lastUpdate < SMOOTH_DELAY) {
    return;
  }
  lastUpdate = currentTime;
  
  // Ak motor nie je zapnutý, postupne zastavíme
  if (!motorEnabled) {
    if (currentSpeed > 0) {
      currentSpeed = max(0, currentSpeed - SMOOTH_STEP);
      updateMotorPWM();
      
      // Keď sa motor úplne zastaví, vypneme enable
      if (currentSpeed == 0) {
        digitalWrite(ENABLE_PIN, LOW);
        currentDirection = 'S';
        Serial.println("Motor VYPNUTÝ");
        printStatus();
      }
    }
    return;
  }
  
  // Zmena smeru - najprv zastavíme, potom rozbehneme v novom smere
  if (motorDirection != currentDirection && currentSpeed > 0) {
    // Postupne spomalíme na 0 (rýchlejšie brzdenie pri zmene smeru)
    currentSpeed = max(0, currentSpeed - (SMOOTH_STEP * 2)); 
    updateMotorPWM();
    
    if (currentSpeed == 0) {
      currentDirection = motorDirection;
      Serial.print("Smer zmenený na: ");
      Serial.println(currentDirection == 'L' ? "ĽAVO" : "PRAVO");
    }
    return;
  }
  
  // Ak sme zastavili kvôli zmene smeru, nastavíme nový smer
  if (motorDirection != currentDirection && currentSpeed == 0) {
    currentDirection = motorDirection;
  }
  
  // Plynulá zmena rýchlosti
  if (currentSpeed != motorSpeed) {
    int oldSpeed = currentSpeed;
    
    if (currentSpeed < motorSpeed) {
      currentSpeed = min(motorSpeed, currentSpeed + SMOOTH_STEP);
    } else {
      currentSpeed = max(motorSpeed, currentSpeed - SMOOTH_STEP);
    }
    
    // Update PWM iba ak sa rýchlosť zmenila
    if (oldSpeed != currentSpeed) {
      updateMotorPWM();
    }
  }
}

void updateMotorPWM() {
  if (currentSpeed == 0) {
    // Zastavenie - vypneme oba kanály
    ledcWrite(PWM_LEFT_CHANNEL, 0);
    ledcWrite(PWM_RIGHT_CHANNEL, 0);
    return;
  }
  
  // Prepočet rýchlosti z % na PWM hodnotu (0-255)
  int pwmValue = map(currentSpeed, 0, 100, 0, 255);
  
  // Obmedzenie PWM hodnoty na platný rozsah
  pwmValue = constrain(pwmValue, 0, 255);
  
  // Nastavenie smeru
  if (currentDirection == 'L') {
    ledcWrite(PWM_LEFT_CHANNEL, pwmValue);   // Ľavý PWM
    ledcWrite(PWM_RIGHT_CHANNEL, 0);         // Pravý PWM vypnutý
  } else if (currentDirection == 'R') {
    ledcWrite(PWM_LEFT_CHANNEL, 0);          // Ľavý PWM vypnutý
    ledcWrite(PWM_RIGHT_CHANNEL, pwmValue);  // Pravý PWM
  } else {
    // Bezpečnostné zastavenie
    ledcWrite(PWM_LEFT_CHANNEL, 0);
    ledcWrite(PWM_RIGHT_CHANNEL, 0);
  }
}

void forceStopMotor() {
  Serial.println("Núdzové zastavenie motora...");
  
  digitalWrite(ENABLE_PIN, LOW);
  ledcWrite(PWM_LEFT_CHANNEL, 0);
  ledcWrite(PWM_RIGHT_CHANNEL, 0);
  
  currentSpeed = 0;
  motorSpeed = 0;
  motorDirection = 'S';
  currentDirection = 'S';
  motorEnabled = false;
  
  Serial.println("Motor kompletne zastavený a vypnutý");
}

void printStatus() {
  Serial.print("Status: ");
  Serial.print(motorEnabled ? "ON" : "OFF");
  Serial.print(" | Smer: ");
  
  switch(currentDirection) {
    case 'L': Serial.print("ĽAVO"); break;
    case 'R': Serial.print("PRAVO"); break;
    default:  Serial.print("STOP"); break;
  }
  
  Serial.print(" | Aktuálna: ");
  Serial.print(currentSpeed);
  Serial.print("% | Cieľová: ");
  Serial.print(motorSpeed);
  Serial.println("%");
  Serial.println("---");
}

void printDetailedStatus() {
  Serial.println("=== DETAILNÝ STATUS ===");
  Serial.print("Systém: ");
  Serial.println(systemReady ? "PRIPRAVENÝ" : "INICIALIZÁCIA");
  Serial.print("Motor: ");
  Serial.println(motorEnabled ? "ZAPNUTÝ" : "VYPNUTÝ");
  Serial.print("Enable pin: ");
  Serial.println(digitalRead(ENABLE_PIN) ? "HIGH" : "LOW");
  Serial.print("Aktuálny smer: ");
  Serial.println(currentDirection);
  Serial.print("Cieľový smer: ");
  Serial.println(motorDirection);
  Serial.print("Aktuálna rýchlosť: ");
  Serial.print(currentSpeed);
  Serial.println("%");
  Serial.print("Cieľová rýchlosť: ");
  Serial.print(motorSpeed);
  Serial.println("%");
  Serial.print("PWM frekvencia: ");
  Serial.print(PWM_FREQUENCY);
  Serial.println(" Hz");
  Serial.println("=====================");
}

bool isNumeric(String str) {
  if (str.length() == 0) return false;
  
  for (unsigned int i = 0; i < str.length(); i++) {
    if (!isDigit(str.charAt(i))) {
      return false;
    }
  }
  return true;
}