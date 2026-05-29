# SceneGen V2 Status

Date: 2026-05-23

Scope: visual scene editor inside `museum-dashboard`.

This file replaces the older long-form SceneGen V2 specification. It tracks what
is already implemented and what is still missing.

## Current Verdict

SceneGen V2 is mostly implemented as a working dashboard-based scene editor.

It is not just a design draft anymore. The main editor route, state editor,
device/media palette, action editing, transitions, and visual timeline already
exist in `museum-dashboard/src`.

The remaining work is mostly polish, validation, full replacement of the old
JSON modal workflow, and a few editor quality-of-life features.

## Done

### Dashboard Route And Navigation

Status: done

Implemented in:

- `museum-dashboard/src/App.jsx`
- `museum-dashboard/src/components/Layout/Sidebar.jsx`
- `museum-dashboard/src/components/Scenes/SceneCard.jsx`
- `museum-dashboard/src/components/Views/ScenesView.jsx`

What exists:

- Route `/scene-editor`.
- Route `/scene-editor/:sceneName`.
- Sidebar entry for the scene editor.
- Scene cards have a V2 editor button using the `Wand2` icon.
- Creating a new scene saves a minimal V2-compatible template and navigates to
  `/scene-editor/<filename>`.

### Main Scene Editor View

Status: done

Implemented in:

- `museum-dashboard/src/components/SceneEditor/SceneEditorView.jsx`
- `museum-dashboard/src/styles/views/scene-editor-v2.css`

What exists:

- Full-page editor view.
- Three-panel layout: state list, state detail editor, palette.
- Dirty-state badge.
- Save button using `api.saveScene`.
- Loading overlay while opening an existing scene.
- State-level test run helper that saves `sc_preview`, stops current scene
  best-effort, and runs the preview scene.

### Scene State Management Hook

Status: done

Implemented in:

- `museum-dashboard/src/hooks/useSceneEditor.js`

What exists:

- Schema-to-internal conversion.
- Internal-to-schema conversion.
- Stable React IDs for editor-only objects.
- State CRUD.
- State rename with `goto` reference propagation.
- Action CRUD.
- onEnter/onExit action reorder.
- Timeline item CRUD and movement.
- Transition CRUD.
- Global events stored in editor state.
- LocalStorage recovery per `sceneName`.
- Backend save support.

### State Metadata Editor

Status: done

Implemented in:

- `museum-dashboard/src/components/SceneEditor/StatePanel.jsx`

What exists:

- State name editing.
- State description editing.
- Initial-state toggle.
- Collapsible sections for onEnter, timeline, onExit, and transitions.

### onEnter / onExit Action Editing

Status: done

Implemented in:

- `museum-dashboard/src/components/SceneEditor/ActionListEditor.jsx`

What exists:

- Add/delete/update actions.
- Drag reorder with `@dnd-kit/sortable`.
- Action type cycle: `mqtt -> audio -> video`.
- MQTT topic field.
- Message/command field.

### Transition Editing

Status: done

Implemented in:

- `museum-dashboard/src/components/SceneEditor/TransitionEditor.jsx`

What exists:

- Transition type dropdown.
- Supported types: `timeout`, `mqttMessage`, `audioEnd`, `videoEnd`, `always`.
- Type-specific parameter fields.
- `goto` dropdown from existing states plus `END`.
- Add/delete/update transitions.

### Device And Media Palette

Status: done

Implemented in:

- `museum-dashboard/src/hooks/useDevicePalette.js`
- `museum-dashboard/src/components/SceneEditor/EditorPalette.jsx`
- existing hooks `useDevices` and `useMedia`

What exists:

- Palette is built from live devices and media data.
- Motors include quick messages such as `ON:50:L`, `ON:50:R`, `OFF`,
  `SPEED:80`, `DIR:L`, and `DIR:R`.
- Relays/lights include quick `ON` and `OFF`.
- Audio items insert `PLAY:<file>:1.0`.
- Video items insert `PLAY_VIDEO:<file>`.
- Audio preview is available from the palette.
- Palette items can be inserted into onEnter/onExit.
- Palette items can be dragged into the visual timeline.

### Visual Timeline

Status: done

Implemented in:

- `museum-dashboard/src/components/SceneEditor/VisualTimeline.jsx`
- `museum-dashboard/src/components/SceneEditor/TimelineTrack.jsx`
- `museum-dashboard/src/components/SceneEditor/TimelineClip.jsx`
- `museum-dashboard/src/components/SceneEditor/TimeRuler.jsx`
- `museum-dashboard/src/components/SceneEditor/TimelineToolbar.jsx`
- `museum-dashboard/src/components/SceneEditor/ClipPopover.jsx`

What exists:

- Three tracks: MQTT, audio, video.
- Timeline clips are point events, matching backend scene schema semantics.
- Time ruler.
- Zoom control.
- Snap toggle.
- Drag/move timeline clips.
- Delete timeline clips.
- Drop palette items onto timeline tracks.
- Popover editing for individual clips.

### Dependencies

Status: done

Implemented in:

- `museum-dashboard/package.json`

What exists:

- `@dnd-kit/core`
- `@dnd-kit/sortable`
- `react-hot-toast`
- `lucide-react`
- `reactflow`
- Monaco editor remains available for the old JSON modal.

## Partly Done

### Replacement Of Old SceneEditorModal

Status: partly done

Current state:

- V2 editor exists and is reachable.
- New scenes navigate to V2 after creation.
- Scene cards expose a V2 editor button.
- The old JSON modal still exists and is still wired from `ScenesView` through
  the regular JSON edit button.

Why this matters:

- Users currently have two editing paths.
- That can be useful during transition, but it is not a clean final state.

Recommended next step:

- Keep the old JSON modal temporarily as "Advanced JSON".
- Rename the buttons clearly:
  - V2 visual editor: primary edit action.
  - JSON modal: advanced/raw JSON action.
- Later remove the old modal if V2 covers all required workflows.

### Global Events

Status: partly done

Current state:

- `useSceneEditor` stores `globalEvents`.
- `internalToSchema` writes `globalEvents`.
- `renameState` updates `globalEvents` goto references.
- There is no visible full editor UI for global events in the V2 page.

Recommended next step:

- Add a small Global Events section to `SceneEditorView` or `StatePanel`.
- Reuse the transition-row editing logic where possible.

### Import / Export JSON

Status: partly done

Current state:

- `useSceneEditor` exposes `exportJSON`.
- `useSceneEditor` exposes `importFromJSON`.
- The V2 page does not currently expose obvious Import/Export buttons.

Recommended next step:

- Add Export JSON button.
- Add Import JSON button.
- Keep save-to-Pi as the main persistence path.

### Flow Graph / JSON Preview Tabs

Status: not done in V2 page

Current state:

- `SceneVisualizer` exists elsewhere.
- The V2 page does not currently include bottom tabs for editor, flow graph, and
  JSON preview.

Recommended next step:

- Add tabs only if they are useful in daily editing.
- A JSON preview panel would be useful for trust and debugging.
- Flow graph can be deferred if it makes the editor too dense.

## Missing

### Frontend Schema Validation Before Save

Priority: high

Problem:

- Backend schema validation exists in `raspberry_pi/utils/schema_validator.py`.
- V2 currently converts editor state to JSON and saves it, but the frontend does
  not provide a clear schema validation pass before save.

Recommended fix:

- Add a frontend validation function mirroring the backend schema.
- Validate before save.
- Show user-friendly errors before sending invalid data to the Pi.

Acceptance:

- Missing `sceneId`, missing `initialState`, invalid action type, invalid
  timeline item, and broken transition shapes are caught before save.

### Broken Transition Target Detection

Priority: high

Problem:

- Rename propagation is implemented.
- Delete-state cleanup removes transitions pointing at deleted states.
- There should still be a final validation/warning pass for transitions whose
  `goto` target does not exist.

Recommended fix:

- Add an editor validation panel or save-blocking warning for unknown `goto`
  values.
- Treat `END` and `__END__` deliberately and consistently.

### Timeline Multi-Action Roundtrip

Priority: medium

Current state:

- Import explodes schema timeline items with `actions[]` into separate clips at
  the same timestamp.
- Export writes separate timeline items, not grouped `actions[]`.

Why this is acceptable:

- Backend schema supports separate timeline items.
- The editor model is simpler: one clip equals one action.

Decision needed:

- Keep this simplification permanently, or add grouping support later.

### Clip Collision Display CHECK THIS IF ITS IMPLEMENTED OR NOT

Priority: medium

Problem:

- Multiple clips at the same `at` value and same track can visually overlap.

Recommended fix:

- Add lane stacking or compact overlap indicators.
- Do not block the data model; the schema allows same-time events.

### Keyboard Shortcuts NOT NEEDED

Priority: low / polish

Missing:

- Delete selected clip.
- Duplicate selected clip/action.
- Undo/redo.

Recommended fix:

- Add only after selection state is explicit and reliable.
- Start with Delete and Duplicate before adding full undo/redo.

### Undo / Redo

Priority: low / polish

Problem:

- Editing complex scenes without undo is risky.

Recommended fix:

- Add a bounded history stack inside `useSceneEditor`.
- Keep localStorage recovery separate from undo history.

### Audio Duration Endpoint

Priority: optional

Current state:

- Timeline events are point events, not duration clips.
- Audio duration is not required for schema correctness.

Possible future use:

- Show media duration metadata in the palette.
- Improve previews and editor hints.

Recommended decision:

- Skip for now unless real editing work needs it.

### Standalone SceneGen Decision THIS WONT BE USED, BUT KEEP IT FOR NOW IN REPO

Priority: medium

Current state:

- Old standalone `SceneGen/` still exists.
- V2 editor is inside `museum-dashboard`, which is architecturally better
  because it has access to backend APIs, devices, media, and scene saving.

Recommended decision:

- Keep `SceneGen/` temporarily as an offline legacy/dev tool.
- Mark it as legacy in its `readme.md`.
- Remove it later if V2 fully replaces the workflow.

### Text Encoding Cleanup

Priority: low

Problem:

- Some existing frontend source files show mojibake in comments and UI strings
  when read from PowerShell output.

Recommended fix:

- Audit file encoding before doing broad text cleanup.
- Do not mix this with functional editor changes.

## Recommended Next Work Order

1. Make V2 the primary edit path in `ScenesView`.
2. Rename the old modal path to "Advanced JSON" or remove it later.
3. Add frontend schema validation before save.
4. Add global events UI.
5. Add JSON preview/export/import controls.
6. Add transition-target validation warnings.
7. Improve overlapping timeline clip display.
8. Decide the future of standalone `SceneGen/`.

## Do Not Reopen As Requirements Without A New Reason

These are already implemented enough for the current editor version:

- Full-page V2 route.
- State CRUD.
- State rename propagation.
- onEnter/onExit editing.
- onEnter/onExit reorder.
- Transition editing.
- Device palette.
- Audio palette.
- Video palette.
- Palette drag/drop into action lists.
- Palette drag/drop into timeline.
- Visual timeline with zoom, snap, ruler, tracks, clips, and popover editing.
- Save to backend.
- LocalStorage recovery.

## Final Note

SceneGen V2 should continue as the dashboard-integrated editor. The standalone
SceneGen app should not receive major new feature work unless there is a clear
offline-only requirement.
