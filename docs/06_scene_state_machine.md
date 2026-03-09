# Štruktúra JSON Scény (Scene Schema)

Tento dokument definuje požadovanú štruktúru JSON súborov pre scény múzejného riadiaceho systému vychádzajúce zo schémy `raspberry_pi/utils/schema_validator.py`.

Každý JSON súbor v zložke `raspberry_pi/scenes/` musí striktne dodržiavať tento kontrakt.

---

## 1. Koreňové vlastnosti (Root Properties)

Pri definícii scény musia byť na najvyššej úrovni definované tieto vlastnosti:

*   **`sceneId`** (string) - **Povinné**. Unikátny identifikátor scény.
*   **`initialState`** (string) - **Povinné**. Názov stavu, v ktorom scéna začína. Tento stav musí byť definovaný v parametri `states`.
*   **`states`** (object) - **Povinné**. Slovník (dictionary) všetkých stavov v scéne.
*   `version` (string) - *Voliteľné*. Verzia scény z pohľadu autora.
*   `description` (string) - *Voliteľné*. Krátky textový popis, čo robí táto scéna.
*   `globalEvents` (array) - *Voliteľné*. Pole prechodov (transitions), ktoré sú aktívne bez ohľadu na to, v akom stave sa scéna práve nachádza. (viď. sekcia Prechody).

### Príklad kmeňa scény:
```json
{
  "sceneId": "Room_Adventures",
  "version": "1.0",
  "initialState": "STATE_IDLE",
  "states": {
    "STATE_IDLE": { ... }
  }
}
```

---

## 2. Definícia Stavu (State)

Každý stav (vnútri objektu `states`) môže obsahovať nasledujúce vlastnosti:

*   `description` (string) - *Voliteľné*. Popis toho, čo sa deje v tomto stave.
*   `onEnter` (array of actions) - *Voliteľné*. Pole akcií, ktoré sa spustia **okamžite** po vstupe do tohto stavu.
*   `onExit` (array of actions) - *Voliteľné*. Pole akcií, ktoré sa spustia **tesne pred opustením** tohto stavu.
*   `transitions` (array of transitions) - *Voliteľné*. Podmienky, pri ktorých splnení systém prejde do iného stavu.
*   `timeline` (array) - *Voliteľné*. Pole časovaných akcií, ktoré sa spúšťajú postupne, kým je stav aktívny.

---

## 3. Akcie (Actions)

Akcie definujú to, čo má systém fyzicky vykonať (prehrať zvuk, poslať príkaz MQTT zariadeniam atď). Používajú sa v `onEnter`, `onExit` a v rámci `timeline` elementov.

Povinným parametrom každej akcie je **`action`**. 
Môže nadobúdať tri hodnoty: `mqtt`, `audio`, `video`.

### Tvar Akcie (Všeobecný):
```json
{
  "action": "mqtt | audio | video",
  "topic": "meno_topicu_pre_mqtt",
  "message": "konkretna_sprava_alebo_subor" 
}
```
*Poznámka:* `retain` (boolean) je takisto podporovaný voliteľný argument pre `mqtt` akcie.

**Špecifické použitie podľa typu:**

*   **`mqtt`**: Používa `topic` (napr. `"room1/light/1"`) a `message` (napr. `"ON"`).
*   **`audio`**: Nepoužíva `topic`. Príkaz a súbor sa posielajú v `message` vo formáte `"PLAY:nazov_suboru.wav:hlasitost"`, `"STOP"`, `"PAUSE"`, `"RESUME"`.
*   **`video`**: Nepoužíva `topic`. Príkaz a súbor sa posielajú priamo v `message` (napr. `"PLAY_VIDEO:subor.mp4"`, `"STOP_VIDEO"`).

---

## 4. Časová línia (Timeline)

Timeline slúži na spúšťanie udalostí po určitom čase strávenom v danom stave. Element v poli timeline musí obsahovať atribút **`at`** (číslo, čas v sekundách).
Následne musí obsahovať buď jednu konkrétnu `action` vlastnosť, ale môže definovať rovno celé pole `actions`.

### Príklad pre timeline:
```json
"timeline": [
  {
    "at": 5,
    "action": "audio",
    "message": "PLAY:scary_sound.mp3:1"
  },
  {
    "at": 10,
    "actions": [
      {
        "action": "mqtt",
        "topic": "room1/light",
        "message": "ON"
      }
    ]
  }
]
```

---

## 5. Prechody (Transitions)

Prechody hovoria State Machine-u kedy a kam prepnúť stav. Používajú sa v `states.nieco.transitions` a v `globalEvents`.
Každý prechod musí nevyhnutne obsahovať parametry: **`type`** a **`goto`**.

### Štruktúra prechodu:
*   **`type`** (string) - Typ podmienky, ktorá musí byť splnená. Najväčšie používané v systéme sú: `timeout`, `mqttMessage`, `audioEnd`, `videoEnd`, `always`.
*   **`goto`** (string) - Názov stavu, do ktorého sa má prejsť. Špeciálne vyhradenou hodnotou je **`END`**, čo signalizuje okamžité vypnutie/dobehnutie scény.

Voliteľné pridružené atribúty prechodu (v závislosti od typu):
*   `delay` (number) - Využívané pri type `timeout` ale aj `always`. Počet sekúnd trvania.
*   `topic` (string) - Využívané pri type `mqttMessage` pre špecifikovanie, na aký MQTT topic sa čaká.
*   `message` (string/number/boolean) - Využívané pri `mqttMessage`, aká správa musí prísť.
*   `target` (string) - Využívané pri `audioEnd/videoEnd` na odsledovanie konca prehrávajucého súboru.

### Príklad prechodu:
```json
"transitions": [
  {
    "type": "timeout",
    "delay": 30,
    "goto": "STATE_NEXT"
  },
  {
    "type": "mqttMessage",
    "topic": "room1/button1",
    "message": "PRESS",
    "goto": "END"
  }
]
```
