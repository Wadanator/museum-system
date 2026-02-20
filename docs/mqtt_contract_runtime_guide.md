# MQTT Contract Runtime Guide (čo systém vezme a čo odignoruje)

Tento dokument popisuje aktuálne správanie MQTT validácie v Raspberry Pi runtime.

## Dopad na systém

- MQTT akcie zo scén sa **pred publishom validujú** (`topic` + `message`).
- Nevalidné MQTT akcie sa **neodošlú** na broker (sú zalogované a ignorované).
- Cieľ: zachytiť chyby skôr, aby sa neposielali zlé príkazy do zariadení.

## Čo systém VEZME (akceptuje)

### 1) Topic musí byť známy pattern
Systém akceptuje tieto skupiny topicov:

- `devices/<id>/status`
- `room<id>/<...>/feedback`
- `room<id>/scene`
- `room<id>/start_scene`
- `room<id>/motor` alebo `room<id>/motor<cislo>`
- `room<id>/light` alebo `room<id>/light/<nieco>`
- `room<id>/effects` alebo `room<id>/effects/<nieco>`
- `room<id>/emergency`
- topic končiaci na `/STOP`
- ostatné topicy s prefixom `room<id>` sú zatiaľ brané ako `room_generic`

### 2) Payload pravidlá podľa typu topicu

- **Motor topicy** (`roomX/motorY`):
  - `ON`, `OFF`
  - `STOP`
  - `SPEED:<0-999>`
  - `ON:<0-999>:L` alebo `ON:<0-999>:R` (voliteľne aj čas `:3000`)
- **Light / Effects / Emergency / Global STOP**:
  - `ON`, `OFF`, `STOP`, `RESET`, `BLINK`
- **Scene trigger** (`roomX/scene`):
  - iba `START`
- **Named scene trigger** (`roomX/start_scene`):
  - názov súboru končiaci `.json`
- **Status / Feedback / room_generic**:
  - aktuálne permissive (kvôli kompatibilite)
- **Čísla a booleany** (`0`, `1`, `False`, `True`) sú povolené pre kompatibilitu so schémou.

## Čo systém ODIGNORUJE (nepošle)

MQTT akcia sa nepošle, ak:

1. `topic` nie je string alebo je prázdny.
2. `message` je `None` alebo prázdny string.
3. `topic` nesedí na podporovaný pattern.
4. `message` nesedí na grammar pre daný topic (napr. `SPEED:30` na light topic).

V týchto prípadoch sa zapíše chyba do logu a publish sa preskočí.

## Ako pridávať nové veci (modularita)

Ak chceš pridať nový typ zariadenia alebo command grammar:

1. **Doplň topic pattern** v `raspberry_pi/utils/mqtt/mqtt_contract.py`.
2. **Rozšír `classify_topic()`** o novú kategóriu.
3. **Doplň validáciu payloadu** v `validate_payload_for_topic()` pre tú kategóriu.
4. (Voliteľne) doplň feedback mapovanie v `get_expected_feedback_topic()`.
5. Otestuj scénu cez validátor a runtime publish.

Takto ostáva core runtime rovnaký a mení sa iba kontraktová vrstva.
