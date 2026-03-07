# Refactoring Core Logic to use Pydantic and Transitions

The objective is to replace custom state machine, validation, and transition logic with `pydantic` and `transitions`, ensuring 1:1 compatibility with existing JSON structures while gaining stability.

## User Review Required
> [!IMPORTANT]
> Please review this plan before execution, as it replaces the core logic of the entire program.
> Note: We will need to install `pydantic` and `transitions` on the Raspberry Pi.

## Proposed Changes

### Core Logic Module

#### [MODIFY] [schema_validator.py](file:///c:/Users/Wajdy/Documents/Kodovanie/museum-system/raspberry_pi/utils/schema_validator.py)
Replace JSonschema-based validation with a robust set of `pydantic` BaseModels.
- Defines `Action`, `Transition`, `TimelineEvent`, `State`, and `SceneModel`.
- Contains custom validators to ensure that `goto` statements reference existing states.
- Provides fully typed objects for the rest of the application.

#### [MODIFY] [state_machine.py](file:///c:/Users/Wajdy/Documents/Kodovanie/museum-system/raspberry_pi/utils/state_machine.py)
Replace custom history/timers with the native `transitions.Machine`.
- Generates dynamic triggers based on the scene's transitions (e.g., `audio_finished_{target}`, `mqtt_{topic}_{message}`).
- Integrates `after_state_change` callbacks to maintain compatibility with the dashboard (`on_state_change`).
- We will keep a small elapsed time tracker for `timeout` and timeline events to maintain the exact 1:1 behavior without risking background thread issues.

#### [DELETE] [transition_manager.py](file:///c:/Users/Wajdy/Documents/Kodovanie/museum-system/raspberry_pi/utils/transition_manager.py)
Delete the transition manager. Event queues are removed. Asynchronous events (like MQTT and Audio) will boldly and directly trigger the `state_machine`.

#### [MODIFY] [scene_parser.py](file:///c:/Users/Wajdy/Documents/Kodovanie/museum-system/raspberry_pi/utils/scene_parser.py)
- `_on_audio_ended` and `_on_video_ended` will run `self.state_machine.trigger(f"audio_finished_{filename}")`.
- `register_mqtt_event` will trigger the machine with `mqtt_{topic}_{payload}`.
- `process_scene` will be simplified to checking timeouts, timelines, and handler ends, rather than evaluating queued events.

#### [MODIFY] [state_executor.py](file:///c:/Users/Wajdy/Documents/Kodovanie/museum-system/raspberry_pi/utils/state_executor.py)
- Update attribute access to dot notation since data now comes via Pydantic (`action.topic` instead of `action.get("topic")`).
- Adjust timeline checking to use the new object models.

## Verification Plan
- Create a test script or use `pytest` to validate that new Pydantic models correctly parse your existing `scenes/*.json`.
- Verify the system still broadcasts `activeState` to the React dashboard.
- Verify MQTT and Audio functionality continue to trigger state transitions correctly.
