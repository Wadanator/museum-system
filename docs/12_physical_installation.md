# Fyzická inštalácia expozície (Physical Installation Reference)

Tento dokument opisuje reálnu fyzickú zostavu expozície, ktorú riadiaci systém ovláda. Slúži ako referencia pre AI pri písaní kapitol o HW implementácii a experimentoch.

---

## 1. Celková dispozícia

- **Rozmer steny expozície:** cca 3 m × 1,5 m (šírka × výška)
- Celá stena tvorí jeden kompaktný tematický celok so steampunk/industriálnou estetikou.
- Celá expozícia je **čisto dizajnová** – žiadny exponát nevykonáva reálnu funkciu (hodiny neukazujú čas, kolesá sa netočia mechanicky, budíky nič nemeria). Všetko slúži ako vizuálny a atmosferický prvok.
- Elektronika je skrytá – návštevník vidí len exponáty, nie riadiacu techniku.
- Inštalácia je pomenovaná **CHRONOS** – tento nápis je fyzicky prítomný na liatinovej tabuľke umiestnenej v dolnej časti steny.

---

## 2. Exponáty a ovládané prvky

### 2.1 Veľké hodiny (motor)
- Dominantný prvok steny – rozmerné dekoratívne hodiny umiestnené hore na stene.
- Ciferník má **rímske číslice** a dekoratívne kované ručičky (biele, ornamentálne).
- **Hodiny sú čisto dekoratívne – neukazujú skutočný čas.** Pohyb ručičiek je riadený systémom ako efekt, nie na základe reálneho času.
- Pohyb hodinových ručičiek je riadený **jednosmerným (DC) motorom** cez H-mostík BTS7960B.
- Motor ovláda uzol `esp32_mqtt_controller_MOTORS` cez topiky `room1/motor1`.
- Hodiny sú podsvietené **LED pásom** (zapínanie cez reléový uzol).

### 2.2 Sústava ozubených kolies
- Na stene je rozmiestnených **~9–10 dekoratívnych ozubených kolies** rôznych veľkostí:
  - 3 veľké kolesá (dominantné, priemer 40–60 cm)
  - 3–4 stredné kolesá
  - 2–3 menšie kolesá
- **Kolesá sú čisto statické a dekoratívne** – nie sú poháňané motorom, slúžia len ako vizuálny prvok steampunk kompozície.
- Všetky kolesá majú **bronzovo-hnedý patinovaný povrch** zodpovedajúci industriálnej estetike celej steny.
- Podsvietené **LED pásom** (zapínanie cez reléový uzol).

### 2.3 Budíky – analógové ukazovatele (relé)
- Vintage ručičkové meracie prístroje (podobné starým meračom napätia a prúdu).
- Slúžia ako dekoratívny prvok s ilúziou „meracej aparatúry" – **nič reálne nemerajú**.
- Fyzicky sú usporiadané do **dvoch skupín** na stene (čomu zodpovedá aj rozdelenie v MQTT topikoch):
  - Skupina A: 2 budíky (napr. „tlak" a „teplota")
  - Skupina B: 1–2 budíky (napr. „výkon" / iný ukazovateľ)
- Vnútorne **podsvietené** – zapínanie každého budíka individuálne cez **reléový uzol** (kanály `light/*`).

### 2.4 Edisonova žiarovka
- Jedna retro dekoratívna Edisonova žiarovka.
- Zapínaná cez **reléový uzol** (samostatný kanál).

### 2.5 Dymostroj s vodiaci trubkou
- Výrobca dymu (smoke machine / fog machine).
- Na výstupe je namontovaná trubka, ktorá vedie dym **smerom nahor** – dym sa vizuálne valí hore po stene/exponátoch.
- Fyzicky je trubkový rozvod riešený **PVC rúrkami** (viditeľné ako Y-rozdeľovač a priame sekcie pod kotlom).
- Ovládanie prebieha v **dvoch krokoch** cez relé uzol:
  1. `power/smoke_ON` – privedenie napájania 230 V na dymostroj (**nahrátie** stroja, musí prejsť tepelnú prípravu).
  2. `effect/smoke` – aktivácia samotnej produkcie dymu (automatické vypnutie po 12 000 ms).
- Napájanie 230 V AC, spínané cez Waveshare reléový modul.

### 2.6 Svetlo „Oheň"
- Jedno svetlo umiestnené pri kotle, simulujúce efekt ohňa / žeravenia.
- Zapínané cez **reléový uzol**, kanál `light/fire`.
- Kombinuje sa s dymostrojom pre dramatický vizuálny efekt.

### 2.7 Vstupné ovládacie tlačidlo
- Senzorický uzol pre interakciu s návštevníkmi, osadený fyzicky oddelene od hlavného kotla na vstupnom mieste pred stenou.
- **Typ tlačidla:** 19 mm vodotesný kovový antivandal spínač so zeleným kruhovým LED podsvietením.
- **Zapojenie:** Tlačidlo a jeho ESP32 DevKit V1 sú osadené v inštalačnej krabičke. Krabička obsahuje na zadnej strane DC jack pre pohodlné privedenie 5 V napájania a vyvedený **GX12 4-pinový konektor** pre samotné tlačidlo.

---

## 3. Skrinka elektroniky – Kotol

- Celá riadiaca elektronika je ukrytá vo **fyzickom kotli** – dominantnom dekoratívnom prvku inštalácie.
- Kotol je súčasťou vizuálu steny – návštevník ho vidí ako exponát (parný kotel), nie ako rozvádzač.

### 3.1 Fyzický popis kotla
- **Tvar:** veľký valcový nádrž s priemerom cca 70–80 cm a výškou cca 60 cm.
- **Povrch:** čierna matná farba s **nitovaným lemom** po obvode vrchnej hrany – autentická industriálna estetika.
- **Veko:** výklopné polguľaté veko s pántom (otvára sa nahor), umožňuje prístup k elektronike.
- **Okienko:** na prednej stene kotla je **štvorcová mriežka (gril)** s priehľadom dnu – za ňou je umiestnené svetlo „Oheň" (`light/fire`), ktoré cez mriežku simuluje žeravenie / oheň.
- **Nožičky:** kotol stojí na **4 kovových nohách** (industriálny štýl).
- **Trubkový rozvod dymu:** pod kotlom vychádzajú PVC rúrky (Y-rozdeľovač + priame sekcie), ktoré vedú dym z dymostroja umiestneného vo vnútri smerom von a nahor po stene.

### 3.2 Obsah kotla (elektronika)
- Vo vnútri kotla sa nachádzajú:
  - **Waveshare ESP32-S3 Relay Module** – 8-kanálový reléový uzol (230 V okruhy: dymostroj, svetlá, budíky, Edisonka, „oheň")
  - **ESP32 DevKit V1** – motorický uzol (riadenie motorov hodín cez BTS7960B)
  - Napájacie vetvy: hlavná 12 V vetva pre reléový modul a výkonové časti, z ktorej je cez DC/DC step-down menič vytvorená 5 V vetva pre ESP32 v motorickom uzle
  - **Dymostroj (fog machine)** – fyzicky umiestnený priamo v kotli; výstupná trubka vedie cez otvor v tele kotla von
- Kotol je prepojený s ostatnými prvkami steny cez kabeláž vedenú za stenou/konštrukciou.

### 3.3 Centrálna jednotka (Raspberry Pi)
- Úlohu hlavného \uv{mozgu} plní Raspberry Pi, ktoré **nie je** súčasťou kotla.
- **Umiestnenie:** Fyzicky inštalované v tesnej blízkosti audiovizuálnej techniky (priamo za obrazovkou monitora).
- **Výstupy:** Zabezpečuje video výstup priamo na monitor cez **HDMI** a natívny audiosignál cez **3,5 mm jack** (odstraňuje nutnosť zbytočne dlhých káblov).

---

## 4. Zhrnutie ovládaných prvkov (mapovanie na systém)

| Exponát | Typ akcie | Zodpovedný uzol | MQTT topik |
|---|---|---|---|
| Hodiny (motor) | PWM pohyb | `esp32_mqtt_controller_MOTORS` | `room1/motor1` |
| LED pás – hodiny | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/1` (alebo iný) |
| LED pás – kolesá | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/2` (alebo iný) |
| Budíky sk. A (podsvietenie) | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/3`, `room1/light/4` |
| Budíky sk. B (podsvietenie) | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/5` (alebo iný) |
| Edisonova žiarovka | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | *(topik doplniť)* |
| Dymostroj – napájanie (ohrev) | Privedenie 230 V, nahrievanie | `esp32_mqtt_controller_RELAY` | `room1/power/smoke_ON` |
| Dymostroj – produkcia dymu | Spúšťač + auto-off 12 s | `esp32_mqtt_controller_RELAY` | `room1/effect/smoke` |
| Svetlo „Oheň" | Zapnutie/vypnutie | `esp32_mqtt_controller_RELAY` | `room1/light/fire` |

> **Poznámka:** Presné mapovanie MQTT topikov na fyzické kanály relé modulu je definované v `Instructions_READ_FIRST/04_mqtt_protocol.md` a `Instructions_READ_FIRST/05_esp32_hardware_reference.md`. Ak sa líši, tieto súbory majú prednosť.

---

## 5. Poznámky k inštalácii

- Celá zostava je navrhnutá ako **jednorazová**, tematicky uzavretá expozícia – nie modulárny showroom.
- Napájanie 230 V pre silové prvky (dymostroj, svetlá) prechádza výhradne cez Waveshare reléový modul s optickým oddelením.
- ESP32 v motorickom uzle je napájané z 12 V vetvy cez DC/DC menič 12 V -> 5 V; vstupný tlačidlový uzol má samostatné 5 V napájanie v inštalačnej krabičke.
- Wi-Fi pokrytie pre MQTT komunikáciu pokrýva celý priestor expozície z jedného dedikovaného prístupového bodu.
- **Všetky exponáty sú čisto vizuálne/dizajnové** – žiadny nevykonáva reálnu meraciu ani časovaciu funkciu. Pohyb, svetlo a dym sú riadené ako efekty scénického charakteru.