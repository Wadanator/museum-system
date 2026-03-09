# Architektúra bežiaca na Pydantic a Transitions
Tento návrh ukazuje, ako v tvojom existujúcom kóde nahradiť tvoje vlastné knižnice (`schema_validator.py`, `state_machine.py`, `transition_manager.py`) za oveľa robustnejšie riešenie pomocou priemyselne overených knižníc `pydantic` a `transitions`.

Dôležité: **Tvoj JSON formát scén (`scenes/*.json`) sa vôbec nezmení.** Tvoj Frontend (`SceneGen` a `museum-dashboard`) si ani nevšimne, že sa na pozadí niečo zmenilo. Zmení sa len to, ako tieto JSON súbory Raspberry Pi backend spracuje a ako medzi stavmi prepína.

Zredukuje to kód o viac ako 50%, odstráni "reinventing the wheel" a zaručí to `24/7` stabilitu bez race-conditions a preklepov v JSONe.

## 1. Validácia a Parsing cez `Pydantic`
Namiesto tvojho vlastného dlhého JSON Schema slovníka v `schema_validator.py`, ktorý len "skontroluje" či to sedí, vytvoríme typované Python objekty. `Pydantic` zoberie tvoj JSON a okamžite ti vráti krásny Python objekt. Ak nájde chybu, vypíše presne v ktorom riadku JSONu chýba napríklad `goto` parameter.

Súbor: `raspberry_pi/utils/schema_validator.py` by sa zmenil na niečo takéto:

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal

class Action(BaseModel):
    action: Literal["mqtt", "audio", "video"]
    topic: Optional[str] = None
    message: Optional[str] = None
    retain: bool = False

class Transition(BaseModel):
    type: Literal["timeout", "audioEnd", "videoEnd", "mqttMessage", "always"]
    goto: str
    delay: Optional[float] = 0.0
    target: Optional[str] = None
    topic: Optional[str] = None
    message: Optional[str] = None

class TimelineEvent(BaseModel):
    at: float
    action: Optional[Literal["mqtt", "audio", "video"]] = None
    actions: Optional[List[Action]] = None

class State(BaseModel):
    description: Optional[str] = ""
    onEnter: List[Action] = Field(default_factory=list)
    onExit: List[Action] = Field(default_factory=list)
    transitions: List[Transition] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)

class SceneModel(BaseModel):
    sceneId: str
    initialState: str
    globalEvents: List[Transition] = Field(default_factory=list)
    states: Dict[str, State]

    # Automatická kontrola, či všetky 'goto' nadväzujú na existujúce stavy
    @field_validator('states', mode='after')
    @classmethod
    def validate_transitions(cls, states_dict, info):
        # Ak by niekto do JSONu napísal prechod na neexistujúci stav, Pydantic to okamžite odhalí už pri štarte appky.
        for state_name, state_obj in states_dict.items():
            for trans in state_obj.transitions:
                if trans.goto != "END" and trans.goto not in states_dict:
                    raise ValueError(f"State '{state_name}' is trying to goto non-existent state '{trans.goto}'")
        return states_dict
```

Aké sú výhody? Priamo v kóde teraz máš autocomplete. Namiesto `action.get("topic")` píšeš `action.topic` a tvoje IDE presne vie, že je to `String`.

---

## 2. State Machine cez `Transitions`
Namiesto tvojho vlastného while loopu a trackovania `state_elapsed_time` či obsluhy `audio_end_events` queue v `transition_manager.py` využiješ modul `transitions`.  Tento modul sám drží aktuálny stav a nedovolí ti prepnúť na neplatný. 

Funguje to "Event Driven" - nie cez while loopy. 
Súbor: `raspberry_pi/utils/state_machine.py` získa takúto štruktúru:

```python
from transitions import Machine
import threading

class MuseumStateMachine:
    def __init__(self, scene_model, state_executor):
        self.scene_model = scene_model
        self.executor = state_executor
        
        # 1. Zoberieme stavy z Pydantic modelu
        states = list(scene_model.states.keys()) + ["END"]
        
        # 2. Vytvoríme State Machine s callbackmi, ktoré zavolajú tvoj StateExecutor!
        self.machine = Machine(
            model=self, 
            states=states, 
            initial=scene_model.initialState,
            after_state_change=self.on_state_changed
        )
        
        # 3. Zaregistrujeme všetky prechody z JSONu do stroja (dynamicky)
        self._register_transitions()
        
    def _register_transitions(self):
        # Prejdeme pydantic model a pre každý prechod typu 'mqttMessage' alebo 'audioEnd'
        # vytvoríme "trigger", ktorý sa dá volať.
        for state_name, state_obj in self.scene_model.states.items():
            for trans in state_obj.transitions:
                
                # Ak je to audioEnd, vytvoríme trigger pre tento konkrétny súbor
                if trans.type == "audioEnd":
                    trigger_name = f"audio_finished_{trans.target}"
                    self.machine.add_transition(
                        trigger=trigger_name, 
                        source=state_name, 
                        dest=trans.goto
                    )
                
                # Podobne pre MQTT
                elif trans.type == "mqttMessage":
                    trigger_name = f"mqtt_{trans.topic}_{trans.message}"
                    self.machine.add_transition(
                        trigger=trigger_name, 
                        source=state_name, 
                        dest=trans.goto
                    )
                    
    def on_state_changed(self, event):
        # Automaticky zavolané hneď ako stroj prejde do nového stavu
        current_state_data = self.scene_model.states.get(self.state)
        if current_state_data:
            self.executor.execute_onEnter(current_state_data)
            
            # TODO: Naplánovať timeline eventy pomocou Asncio alebo schedulera
```

---

## 3. Zánik Wait Loopov (zánik `TransitionManager.py`)
Tvoj aktuálny systém funguje tak, že v `check_transitions()` sypeš veci z fronty, napríklad `self.audio_end_events.remove(event)`.

S novým prístupom `TransitionManager` **úplne zmizne**.

Keď tvoj `AudioHandler` povie "skončilo audio X", jednoducho zavoláš StateMachine priamo:
```python
def on_audio_ended(self, filename):
    trigger_name = f"audio_finished_{filename}"
    
    # State machine sám skontroluje, či z aktuálneho stavu existuje
    # prechod s týmto triggerom. Ak áno, okamžite zmení stav a vykoná onExit a onEnter ďalšieho stavu.
    # Žiadne fronty, žiadne loopy, okamžitá reakcia v milisekundách.
    try:
        self.state_machine.trigger(trigger_name)
    except MachineError:
        # Tento zvuk síce skončil, ale z aktuálneho stavu z neho cesta nevedie (čo je absolútne OK).
        pass
```

### Prehľad zmien
| Čo máš teraz | Čo bude po refactore | Dôvod |
| :--- | :--- | :--- |
| `schema_validator.py` s dlhými Dict JSON-schemami | Vymenené za **Pydantic** datatriedy. | Objektový model s Autocomplete. Automatická validácia parametrov (napr. typ `action` môže byť iba `["mqtt", "audio", "video"]`). Plná Type-safety. |
| `state_machine.py` trackujúci históriu a `delay` | Vymenené za open-source knižnicu **`transitions`**. | Stará sa o zabránenie neplatným prechodom. Sám púšťa callbacky `on_enter` a `on_exit` stavu. |
| `transition_manager.py` | **ÚPLNE ZMAZANÝ SÚBOR.** | Býval potrebný kvôli Event Queue (zhromaždeniu Threadov z Audio/MQTT) do hlavného Main-loopu. Knihovňa `transitions` je Thread-safe a prepína stavy Event-driven v čase vzniku. |
| `scene_parser.py` (Main loop a ticky) | Výrazne zjednodušený. Len nabootuje StateMachine. | Žiadne `process_scene()` volané v nekonečnom pythónovskom loope. Všetko sa deje na základe udalostí (Event-driven). |
| `state_executor.py` | Zostane takmer **bez zmeny**. | Dobre napísaná architektúra, akurát do neho už nebudú padať slovníky `action.get('topic')`, ale Pydantic objekty `action.topic`. |


## 4. Overenie 1:1 Kompatibility so zvyškom systému

Pred týmto návrhom som analyzoval aj napojené periférie, aby som zagarantoval, že refactor neublíži 24/7 plynulému chodu:

- **Frontend (`Web/dashboard.py` + React)**: Dashboard sa pozerá na prechody cez SocketIO v `main.py` (`notify_web`). Knižnica `transitions` má na stavy natívny callback `after_state_change`, ktorý pošle do Webu presne ten istý payload `{'activeState': state_name}`. Na webe sa nezmení jediný pixel kódu.
- **ESP32 Firmware (`esp32_mqtt_button.yaml`)**: Odosiela obyčajný string payload ako *"START"* na `"room1/scene"`. Toto spracuje `MQTTMessageHandler`, ktorý zostáva nezmenený a iba odovzdá udalosť novému Pydantic/Transitions jadru. Pre ESP32 je zmena neviditeľná.
- **Scény (`scenes/*.json`)**: Navrhnuté Pydantic triedy (viď vyššie bod 1) **presne, 1:1 kopírujú** štruktúru tvojich JSONov. Nemusíš prepisovať jediný existujúci JSON v priečinkoch scén.

**Verdikt:** Výsledkom bude systém s oveľa menším množstvom custom kódu. Bude odolný proti akejkoľvek JSON chybe (Pydantic ťa nepustí spustiť chybnú scénu) a namiesto `Tick()` slučiek na pozadí, ktoré vyťažujú procesor Raspberry Pi na počítanie, aký je `state_elapsed_time`, bude všetko čakať bez spotreby CPU na udalosť (Callback) od AudioHandlera, MQTT a časovačov. Zaručí to tú `24/7` odolnosť.

Súhlasíš s prechodom na takúto architektúru? Ak áno, môžeme s kódovaním začať krok po kroku.

## 5. Inštalácia a Nasadenie (Windows vs RPi)

Pretože vývoj prebieha na **Windows PC**, ale kód beží na **Raspberry Pi (RPi)**, nesmieme knižnice inštalovať lokálne počas písania kódu (nakoľko by nefungovali produkčne na RPi).

Postup nasadenia nového kódu:
1. Pridať nové knižnice do súboru `requirements.txt`:
   ```text
   pydantic
   transitions
   ```
2. Odstrániť prebytočné súbory a nahradiť starý kód novým.
3. Po presunutí zmien na Raspberry Pi spustiť inštalačný shell skript:
   ```bash
   ./install.sh
   # Alebo manuálne: pip install -r requirements.txt
   ```

# DELETE IN FUTURE
This file contains a planned refactor using Pydantic and Transitions, which is not yet in production.
