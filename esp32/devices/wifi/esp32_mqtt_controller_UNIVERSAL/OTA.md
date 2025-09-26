# 📡 ESP32 OTA - Návod na používanie

## 🎯 Predpoklady

- ✅ ESP32 má už nahraný kód s OTA podporou
- ✅ ESP32 je zapnutý a pripojený na WiFi
- ✅ Arduino IDE je nainštalované
- ✅ PC a ESP32 sú na rovnakej WiFi sieti

---

## 🚀 Nahrávanie nového kódu (OTA)

### 1. Otvor Arduino IDE
- Spusti Arduino IDE
- Otvor svoj projekt s novým kódom

### 2. Nájdi ESP32 v sieti
**Tools → Port**

Uvidíš dva typy portov:
```
Serial ports:           ← Fyzické káble
├── COM3 (Arduino Uno)
├── COM4 (ESP32)

Network ports:          ← Bezdrôtové ESP32 ⭐
├── ESP32-Museum-Room1 at 192.168.0.150
├── ESP32-Museum-Room2 at 192.168.0.151
└── ESP32-Museum-Room3 at 192.168.0.152
```

### 3. Vyber Network port
- Klikni na **"ESP32-Museum-Room1 at 192.168.x.x"**
- ✅ Port je teraz nastavený

### 4. Upload kód
- Stlač **Ctrl+U** (alebo tlačidlo Upload ➡️)
- Čakaj kým sa dokončí upload
- ESP32 sa automaticky reštartuje s novým kódom

### 5. Hotovo! 🎉
- Nový kód je nahraný
- ESP32 beží s aktualizovaným firmware

---

## 🔍 Čo ak sa Network port nezobrazuje?

### Skontroluj sieťové pripojenie:
```bash
# Windows - nájdi ESP32 v sieti
ping ESP32-Museum-Room1.local

# Alebo skontroluj IP v routeri
# Router admin: 192.168.1.1 → Connected devices
```

### Restart sequence:
1. **Odpoj ESP32** z napájania (5 sekúnd)
2. **Zapoj naspäť** 
3. **Počkaj 30 sekúnd** (WiFi pripojenie)
4. **Refresh Arduino IDE** → Tools → Port

### Skontroluj WiFi:
- ESP32 a PC sú na **rovnakej WiFi sieti**
- WiFi credentials v ESP32 kóde sú **správne**
- Router neblokuje **port 3232** (OTA port)

---

## 🖥️ Arduino IDE nastavenia

### Pred uploadom skontroluj:
```
Tools menu:
├── Board: "ESP32 Dev Module"        ✅
├── Upload Speed: "921600"           ✅  
├── Flash Size: "4MB (32Mb)"         ✅
├── Partition Scheme: "Default 4MB"  ✅
└── Port: "ESP32-Museum-Room1..."    ⭐ DÔLEŽITÉ!
```

### Upload process:
```
1. Compile (Verify) ✅
2. Upload začne...
3. "Connecting to ESP32-Museum-Room1..."
4. "Writing at 0x00010000... (10%)"
5. "Writing at 0x00020000... (50%)"  
6. "Hash of data verified."
7. "Leaving... Hard resetting via RTS pin..."
8. Upload complete! ✅
```

---

## ⚡ Rýchly workflow

### Každodenné používanie:
```
1. Otvor Arduino IDE
2. Uprav kód  
3. Tools → Port → "ESP32-Museum-Room1..."
4. Ctrl+U (Upload)
5. Hotovo!
```

### Pre viac ESP32:
```
1. Vyber správny port:
   - ESP32-Museum-Room1 → Room 1 zariadenie  
   - ESP32-Museum-Room2 → Room 2 zariadenie
2. Upload na vybrané zariadenie
3. Opakuj pre ďalšie zariadenia
```

---

## 🕐 Timing a čakanie

### Upload trvanie:
- **Malý sketch** (100KB): ~10 sekúnd
- **Veľký sketch** (1MB): ~60 sekúnd
- **Celý projekt**: ~30 sekúnd

### Po uploade:
- ESP32 sa **automaticky reštartuje**
- Nový kód sa spustí **okamžite**
- OTA zostáva **aktívny** pre ďalšie uploady

---

## 🚨 Riešenie problémov

### "No response from device" chyba:
```
✅ Riešenie:
1. Skontroluj že ESP32 nie je zaneprázdnený (scene beží)
2. Počkaj 1 minútu a skús znovu
3. Reštartuj ESP32 (power cycle)
```

### "Connection timeout" chyba:
```
✅ Riešenie:  
1. Skontroluj WiFi signál ESP32
2. Presun bližšie k routeru
3. Reštartuj router ak treba
```

### "Authentication failed" chyba:
```
✅ Riešenie:
1. V config.cpp je nastavené: OTA_PASSWORD = ""
2. Ak je heslo nastavené, skontroluj správnosť
```

### Upload je pomalý:
```
✅ Zrýchli:
1. Tools → Upload Speed → "921600"  
2. Tools → Flash Frequency → "80MHz"
3. Skontroluj WiFi signál
```

---

## 📊 Status info

### ESP32 Serial výpis po štarte:
```
=== OTA READY ===
Hostname: ESP32-Museum-Room1
IP: 192.168.0.150
Look for 'ESP32-Museum-Room1' in Arduino IDE Network ports
================
```

### V Arduino IDE po výbere Network portu:
```
Selected port: ESP32-Museum-Room1 at 192.168.0.150 (ESP32 Dev Module)
```

---

## 🎯 Benefity OTA

### Bez káblov:
- ✅ Zariadenie môže byť kdekoľvek s WiFi
- ✅ Žiadne rozobieranie boxov/krytov
- ✅ Update z pohodlia kancelárie

### Rýchle deploymenty:
- ✅ Oprav bug → Upload → Hotovo v minúte
- ✅ Viac zariadení súčasne
- ✅ Vzdialené zariadenia (iná budova)

### Development friendly:
- ✅ Iteratívny vývoj bez káblov
- ✅ Test na reálnom zariadení
- ✅ Rýchle prototypovanie

---

## 💡 Pro tipy

### Súbežné uploady:
```
Môžeš nahrávať na viac ESP32 súčasne:
1. Otvor viac okien Arduino IDE
2. Každé okno vyber iný Network port  
3. Upload na všetky súčasne
```

### Backup kód:
```
Vždy si zachovaj funkčnú verziu:
- Ak nový kód nefunguje
- ESP32 sa reštartne s chybným kódom
- Môžeš rýchlo nahrať späť starú verziu
```

### Network discovery:
```bash
# Nájdi všetky ESP32 v sieti (Windows)
arp -a | findstr "30:ae:a4"

# Linux/Mac  
nmap -sn 192.168.1.0/24
```

**OTA = Over-The-Air = Programovanie bez káblov! 🚀**