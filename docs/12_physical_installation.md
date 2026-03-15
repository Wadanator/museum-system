# Fyzická inštalácia expozície (Physical Installation Reference)

Tento dokument opisuje reálnu fyzickú zostavu expozície, ktorú riadiaci systém ovláda. Slúži ako referencia pre AI pri písaní kapitol o HW implementácii a experimentoch.

---

## 1. Celková dispozícia

- **Rozmer steny expozície:** cca 3 m × 1,5 m (šírka × výška)
- Celá stena tvorí jeden kompaktný tematický celok so steampunk/industriálnou estetikou.
- Elektronika je skrytá - návštevník vidí len exponáty, nie riadiacu techniku.

---

## 2. Exponáty a ovládané prvky

### 2.1 Veľké hodiny (motor)
- Dominantný prvok steny - rozmerné dekoratívne hodiny umiestnené hore na stene.
- Pohyb hodinových ručičiek je riadený **jednosmerným (DC) motorom** cez H-mostík BTS7960.
- Motor ovláda uzol `esp32_mqtt_controller_MOTORS` cez topiky `room1/motor1`.
- Hodiny sú podsvietené **LED pásom** (zapínanie cez reléový uzol).

### 2.2 Sústava ozubených kolies
- Niekoľko veľkých dekoratívnych ozubených kolies na stene.
- Statické (nepohybujú sa motorom) - sú vizuálnym prvkom kompozície.
- Podsvietené **LED pásom** (zapínanie cez reléový uzol).

### 2.3 Budíky - analógové ukazovatele (relé)
- Vintage ručičkové meracie prístroje (podobné starým meračom napätia a prúdu).
- Slúžia ako dekoratívny prvok s ilúziou „meracej aparatúry".
- Vnútorne **podsvietené** - zapínanie každého budíka individuálne cez **reléový uzol** (kanály `light/*`).
- Nie sú funkčné meracie prístroje - ide o vizuálny efekt.

### 2.4 Edisonova žiarovka
- Jedna retro dekoratívna Edisonova žiarovka.
- Zapínaná cez **reléový uzol** (samostatný kanál).

### 2.5 Dymostroj s vodiaci trubkou
- Výrobca dymu (smoke machine / fog machine).
- Na výstupe je namontovaná trubka, ktorá vedie dym **smerom nahor** - dym sa vizuálne valí hore po stene/exponátoch.
- Ovládanie prebieha v **dvoch krokoch** cez relé uzol:
  1. `power/smoke_ON` - privedenie napájania 230 V na dymostroj (**nahrátie** stroja, musí prevšť tepelnú prípravu).
  2. `effect/smoke` - aktivácia samotnej produkcie dymu (automatické vypnutie po 12 000 ms).
- Napájanie 230 V AC, spínané cez Waveshare reléový modul.

### 2.6 Svetlo „Oheň"
- Jedno svetlo umiestňené pri kotle, simulujúce efekt ohňa / žeravenia.
- Zapínané cez **reléový uzol**, kanál `light/fire`.
- Kombinuje sa s dymostrojom pre dramatický vizuálny efekt.

---

## 3. Skrinka elektroniky - Kotol

- Celá riadiaca elektronika je ukrytá vo **fyzickom kotli** (dekoratívny prvok inštalácie).
- Kotol je súčasťou vizuálu steny - návštevník ho vidí ako exponát, nie ako rozvádzač.
- Vo vnútri kotla sa nachádzajú:
  - **Waveshare RP2350 Relay Module** - 8-kanálový reléový uzol (230 V okruhy: dymostoj, svetlá, budíky, Edisonka, „oheň")
  - **ESP32 DevKit V1** - motorický uzol (riadenie motorov hodín cez BTS7960)
  - Napájacie zdroje (5 V pre logiku, 12 V pre motory)
- Kotol je prepojený s ostatnými prvkami steny cez kabeláž vedenú za stenou/konštrukciou.

---

## 4. Zhrnutie ovládaných prvkov (mapovanie na systém)

| Exponát | Typ akcie | Zodpovedný uzol | MQTT topik |
|---|---|---|---|
| Hodiny (motor) | PWM pohyb | `esp32_mqtt_controller_MOTORS` | `room1/motor1` |
| LED pás - hodiny | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/1` (alebo iný) |
| LED pás - kolesá | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/2` (alebo iný) |
| Budíky (podsvietenie) | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/3..5` (individuálne) |
| Edisonova žiarovka | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | *(topik doplniť)* |
| Dymostroj - napájanie (ohrev) | Privedenie 230 V, nahrievanie | `esp32_mqtt_controller_RELAY` | `room1/power/smoke_ON` |
| Dymostroj - produkcia dymu | Spúšťač + auto-off 12 s | `esp32_mqtt_controller_RELAY` | `room1/effect/smoke` |
| Svetlo „Oheň" | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/fire` |

> **Poznámka:** Presné mapovanie MQTT topikov na fyzické kanály relé modulu je definované v `Instructions_READ_FIRST/04_mqtt_protocol.md` a `Instructions_READ_FIRST/05_esp32_hardware_reference.md`. Ak sa líši, tieto súbory majú prednosť.

---

## 5. Poznámky k inštalácii

- Celá zostava je navrhnutá ako **jednorazová**, tematicky uzavretá expozícia - nie modulárny showroom.
- Napájanie 230 V pre silové prvky (dymostroj, svetlá) prechádza výhradne cez Waveshare reléový modul s optickým oddelením.
- ESP32 uzly sú napájané z vlastných 5 V USB-C adaptérov vnútri kotla.
- Wi-Fi pokrytie pre MQTT komunikáciu pokrýva celý priestor expozície z jedného dedikovaného prístupového bodu.
