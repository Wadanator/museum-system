// Motor PWM Control s 20kHz a Smooth operáciami - OPRAVENÁ VERZIA PRE ESP32
// Kompatibilné s Arduino Core 2.x aj 3.x
// Ovládanie motora cez sériový port s plynulým rozbehom/brzdením
// Príkazy: ON, OFF, L, R, číslo 0-100 pre rýchlosť

// Definície pinov
#define PWM_LEFT_PIN 27      // PWM pin pre ľavý smer
#define PWM_RIGHT_PIN 26     // PWM pin pre pravý smer
#define ENABLE_PIN 25        // Enable pin pre motor driver

// Nastavenia pre smooth operácie
#define SMOOTH_STEP 2        // Krok zmeny rýchlosti
#define SMOOTH_DELAY 20      // Pauza medzi krokmi v ms
#define PWM_FREQUENCY 20000  // 20kHz PWM frekvencia
#define PWM_RESOLUTION 8     // 8-bit rozlíšenie (0-255)

// PWM kanály pre ESP32
#define PWM_LEFT_CHANNEL 0
#define PWM_RIGHT_CHANNEL 1

// Premenné
int motorSpeed = 0;
int currentSpeed = 0;
char motorDirection = 'S';
char currentDirection = 'S';
bool motorEnabled = false;
unsigned long lastUpdate = 0;
bool systemReady = false;

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("=== INICIALIZACIA MOTOR PWM CONTROL ===");

  // Najprv nastavíme všetky piny ako výstupy a vypneme ich
  pinMode(PWM_LEFT_PIN, OUTPUT);
  pinMode(PWM_RIGHT_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  
  digitalWrite(PWM_LEFT_PIN, LOW);
  digitalWrite(PWM_RIGHT_PIN, LOW);
  digitalWrite(ENABLE_PIN, LOW);
  
  Serial.println("Piny nastavené a vypnuté");

  // Nastavenie PWM
  if (!setupPWMFrequency()) {
    Serial.println("CHYBA: Nepodarilo sa nastaviť PWM!");
    while(1) delay(1000);
  }

  forceStopMotor();
  delay(100);
  testPWMChannels();
  
  systemReady = true;
  Serial.println("=== MOTOR PWM CONTROL 20kHz + SMOOTH ===");
  Serial.println("Príkazy:");
  Serial.println("  ON       - zapnúť motor");
  Serial.println("  OFF      - vypnúť motor");
  Serial.println("  L        - smer doľava");
  Serial.println("  R        - smer doprava");
  Serial.println("  0-100    - nastaviť rýchlosť (%)");
  Serial.println("  STATUS   - zobraziť aktuálny stav");
  Serial.println("========================================");
  printStatus();
}

void loop() {
  if (!systemReady) {
    delay(100);
    return;
  }

  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toUpperCase();
    if (input.length() > 0) {
      processCommand(input);
    }
  }

  smoothMotorUpdate();
}

bool setupPWMFrequency() {
  Serial.println("Nastavujem PWM...");
  
  // NOVÉ API pre Arduino Core 3.x (kompatibilné aj s 2.x)
  // Použijeme ledcAttach ktoré vracia frekvenciu
  double freq_left = ledcAttach(PWM_LEFT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);
  if (freq_left == 0) {
    Serial.println("CHYBA: Ľavý PWM kanál zlyhal!");
    return false;
  }
  Serial.print("Ľavý kanál OK (");
  Serial.print(freq_left);
  Serial.println(" Hz)");
  
  double freq_right = ledcAttach(PWM_RIGHT_PIN, PWM_FREQUENCY, PWM_RESOLUTION);
  if (freq_right == 0) {
    Serial.println("CHYBA: Pravý PWM kanál zlyhal!");
    return false;
  }
  Serial.print("Pravý kanál OK (");
  Serial.print(freq_right);
  Serial.println(" Hz)");
  
  // Nastavíme PWM na 0
  ledcWrite(PWM_LEFT_PIN, 0);
  ledcWrite(PWM_RIGHT_PIN, 0);
  
  Serial.println("PWM úspešne nakonfigurované");
  return true;
}

void testPWMChannels() {
  Serial.println("Test PWM kanálov...");
  
  ledcWrite(PWM_LEFT_PIN, 50);
  delay(100);
  ledcWrite(PWM_LEFT_PIN, 0);
  
  ledcWrite(PWM_RIGHT_PIN, 50);
  delay(100);
  ledcWrite(PWM_RIGHT_PIN, 0);
  
  Serial.println("Test PWM dokončený");
}

void processCommand(String cmd) {
  Serial.print("Príkaz: ");
  Serial.println(cmd);

  if (cmd == "ON") {
    motorEnabled = true;
    digitalWrite(ENABLE_PIN, HIGH);
    Serial.println("Motor ZAPNUTÝ");
  }
  else if (cmd == "OFF") {
    motorEnabled = false;
    motorSpeed = 0;
    Serial.println("Motor sa vypína...");
  }
  else if (cmd == "L") {
    if (motorDirection != 'L') {
      motorDirection = 'L';
      Serial.println("Smer: ĽAVO");
    }
  }
  else if (cmd == "R") {
    if (motorDirection != 'R') {
      motorDirection = 'R';
      Serial.println("Smer: PRAVO");
    }
  }
  else if (cmd == "STATUS") {
    printDetailedStatus();
    return;
  }
  else if (isNumeric(cmd)) {
    int speed = cmd.toInt();
    if (speed >= 0 && speed <= 100) {
      motorSpeed = speed;
      Serial.print("Cieľová rýchlosť: ");
      Serial.print(motorSpeed);
      Serial.println("%");
      
      if (speed > 0 && !motorEnabled) {
        Serial.println("Automaticky zapínam motor...");
        motorEnabled = true;
        digitalWrite(ENABLE_PIN, HIGH);
      }
    } else {
      Serial.println("CHYBA: Rýchlosť musí byť 0-100");
    }
  }
  else {
    Serial.println("CHYBA: Neznámy príkaz");
    Serial.println("Platné príkazy: ON, OFF, L, R, 0-100, STATUS");
  }
  
  printStatus();
}

void smoothMotorUpdate() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastUpdate < SMOOTH_DELAY) {
    return;
  }
  lastUpdate = currentTime;

  if (!motorEnabled) {
    if (currentSpeed > 0) {
      currentSpeed = max(0, currentSpeed - SMOOTH_STEP);
      updateMotorPWM();
      
      if (currentSpeed == 0) {
        digitalWrite(ENABLE_PIN, LOW);
        currentDirection = 'S';
        Serial.println("Motor VYPNUTÝ");
        printStatus();
      }
    }
    return;
  }

  if (motorDirection != currentDirection && currentSpeed > 0) {
    currentSpeed = max(0, currentSpeed - (SMOOTH_STEP * 2));
    updateMotorPWM();
    
    if (currentSpeed == 0) {
      currentDirection = motorDirection;
      Serial.print("Smer zmenený na: ");
      Serial.println(currentDirection == 'L' ? "ĽAVO" : "PRAVO");
    }
    return;
  }

  if (motorDirection != currentDirection && currentSpeed == 0) {
    currentDirection = motorDirection;
  }

  if (currentSpeed != motorSpeed) {
    int oldSpeed = currentSpeed;
    
    if (currentSpeed < motorSpeed) {
      currentSpeed = min(motorSpeed, currentSpeed + SMOOTH_STEP);
    } else {
      currentSpeed = max(motorSpeed, currentSpeed - SMOOTH_STEP);
    }
    
    if (oldSpeed != currentSpeed) {
      updateMotorPWM();
    }
  }
}

void updateMotorPWM() {
  if (currentSpeed == 0) {
    ledcWrite(PWM_LEFT_PIN, 0);
    ledcWrite(PWM_RIGHT_PIN, 0);
    return;
  }

  int pwmValue = map(currentSpeed, 0, 100, 0, 255);
  pwmValue = constrain(pwmValue, 0, 255);

  if (currentDirection == 'L') {
    ledcWrite(PWM_LEFT_PIN, pwmValue);
    ledcWrite(PWM_RIGHT_PIN, 0);
  }
  else if (currentDirection == 'R') {
    ledcWrite(PWM_LEFT_PIN, 0);
    ledcWrite(PWM_RIGHT_PIN, pwmValue);
  }
  else {
    ledcWrite(PWM_LEFT_PIN, 0);
    ledcWrite(PWM_RIGHT_PIN, 0);
  }
}

void forceStopMotor() {
  Serial.println("Núdzové zastavenie motora...");
  digitalWrite(ENABLE_PIN, LOW);
  ledcWrite(PWM_LEFT_PIN, 0);
  ledcWrite(PWM_RIGHT_PIN, 0);
  currentSpeed = 0;
  motorSpeed = 0;
  motorDirection = 'S';
  currentDirection = 'S';
  motorEnabled = false;
  Serial.println("Motor kompletne zastavený");
}

void printStatus() {
  Serial.print("Status: ");
  Serial.print(motorEnabled ? "ON" : "OFF");
  Serial.print(" | Smer: ");
  
  switch(currentDirection) {
    case 'L': Serial.print("ĽAVO"); break;
    case 'R': Serial.print("PRAVO"); break;
    default: Serial.print("STOP"); break;
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
  Serial.print("Enable pin (GPIO25): ");
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