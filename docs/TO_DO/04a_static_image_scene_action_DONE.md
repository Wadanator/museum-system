# TODO: Static Image Action in Scene JSON

## Progress marking rule

When any concrete item, phase, or section from this plan is implemented, mark
that exact part with `DONE` in this file. Keep the original task text, add a
short date or note if useful, and do not leave completed work only in chat or
git history.

Do not delete TODO items just because they are implemented. The TODO file should
stay useful as project history:

- keep the original task/phase text,
- add `DONE` directly to the implemented heading or bullet,
- add a short completion note with date, changed files, and key tests when it
  helps future work,
- if only part of a section is finished, mark only that part as `DONE`,
- if a section is intentionally skipped or replaced, mark it as `SKIPPED` or
  `SUPERSEDED` with the reason and the replacement location,
- do not rely on chat history, memory files, or git history as the only record
  of completed TODO work.

Whole-file completion rule:

- When every phase in this file is finished or intentionally closed, mark each
  phase as `DONE`, `SKIPPED`, or `SUPERSEDED` inside this file first.
- Then rename this file to `04a_static_image_scene_action_DONE.md` so the file
  list clearly shows that the whole image-action plan is complete.
- Keep the renamed file in `docs/TO_DO/` unless a separate cleanup task moves
  completed plans elsewhere.

## What we want

Add a dedicated JSON scene action for showing a static image on the display.
The behavior should be simple and explicit:

| Intent                | Scene action                                | Meaning                                                            |
| --------------------- | ------------------------------------------- | ------------------------------------------------------------------ |
| Show a specific image | `image` action with image filename        | Replace the display with that image and keep it there              |
| Clear the image       | `image` action with clear/default command | Return to the configured default/idle image, usually `black.png` |

The feature should not create a second display system. It should reuse the
existing mpv/video display process because the screen, IPC socket, fullscreen
behavior, idle image, and crash recovery are already managed there.

## Proposed scene JSON contract

Canonical format:

```json
{
  "action": "image",
  "message": "SHOW:wallpaper.png"
}
```

Clear/default format:

```json
{
  "action": "image",
  "message": "CLEAR"
}
```

Recommended compatibility alias:

```json
{ "action": "image", "message": "DEFAULT" }
```

Rationale:

- `action: "image"` makes scene JSON easier to read than hiding images under
  `action: "video"`.
- `SHOW:<filename>` mirrors the existing command style without adding duration,
  transition, fit, crop, or timing parameters.
- `CLEAR` has no parameter and should always use the configured `iddle_image`.
- `DEFAULT` is accepted as a harmless alias for `CLEAR`.
- `BLACK` should not be accepted as a public alias. It becomes misleading when
  the configured idle/default image is not actually black.
- Bare filenames should not be accepted by the backend for `image` actions.
  If the editor lets a user pick `wallpaper.png`, it should normalize that
  selection to `SHOW:wallpaper.png` before saving the scene JSON.
- Image filenames must be simple basenames, for example `wallpaper.png`, not
  paths such as `room2/videos/wallpaper.png`, `/tmp/wallpaper.png`, or
  `../wallpaper.png`. The active room and media directory are resolved from
  `[Room] room_id`, `[Scenes] directory`, and `[Video] directory` in config.

Naming note:

- The runtime currently uses the existing config/key spelling `iddle_image`
  with a double `d`. This plan keeps that spelling where code references the
  existing field, but new docs/UI labels should call it the idle/default image.

## Compatibility with current behavior

Current video behavior can already display supported image files through the
video handler. That should remain working:

```json
{ "action": "video", "message": "PLAY_VIDEO:wallpaper.png" }
```

The new `image` action is an explicit, cleaner API on top of the same display
backend. Existing scene files must continue to load and run unchanged.

## Difficulty

Medium.

Backend risk is low because `VideoHandler.show_image()` and `stop_video()` are
already the right primitives. The larger part is keeping the JSON schema,
current Raspberry Pi dashboard editor, docs, and tests consistent.

## Files affected

### Backend schema and runtime

#### [MODIFY] `raspberry_pi/utils/schema_validator.py`

- Add `image` to the allowed action enum.
- Require non-empty `message` for `image` actions.
- Add runtime validation for image command shape:
  - `SHOW:<filename>` requires a filename.
  - `SHOW:` with an empty filename is invalid.
  - `CLEAR` and `DEFAULT` are allowed clear/default aliases.
  - bare filenames are invalid in saved JSON and should be normalized by the
    editor before validation.
  - filenames with path separators, parent-directory traversal, absolute paths,
    or NUL bytes are invalid.
  - unsupported media extensions are invalid for `image` actions. Reject at
    least `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`, `.mp3`, `.wav`, and `.ogg`.
  - supported image extensions are `.png`, `.jpg`, and `.jpeg`.
  - `message` must be a string for `image`, even though MQTT messages can still
    be numbers or booleans.

#### [ADD] `raspberry_pi/utils/image_command.py`

- Keep dedicated image command parsing in a small shared helper so
  `schema_validator.py` and `state_executor.py` enforce the same rules.
- Accepted parse results:
  - `SHOW:<safe_filename>` -> show image
  - `CLEAR` / `DEFAULT` -> clear to idle/default image
- Rejected parse inputs:
  - bare filenames,
  - empty `SHOW:`,
  - unsupported extensions,
  - unsafe paths,
  - non-string messages.

#### [MODIFY] `raspberry_pi/utils/state_executor.py`

- Register a new action handler:

```python
self.action_handlers = {
    "mqtt": self._execute_mqtt,
    "audio": self._execute_audio,
    "video": self._execute_video,
    "image": self._execute_image,
}
```

- Implement `_execute_image(action)`.
- Reuse `self.video_handler`; do not create a separate image handler.
- Behavior:
  - `SHOW:<filename>` -> `video_handler.show_image(filename)`
  - `CLEAR` / `DEFAULT` -> `video_handler.stop_video()`
  - bare filename -> invalid for backend image actions; log an error and return
    false from `_execute_image()` if it reaches runtime despite validation.
- If `video_handler` is missing, log the same kind of simulation warning used
  for audio/video.
- `StateExecutor._execute_action()` currently does not propagate handler return
  values to the scene loop. The boolean return from `_execute_image()` is for
  local correctness and unit tests, not for controlling scene progression.

#### [OPTIONAL MODIFY] `raspberry_pi/utils/video/playback.py`

Only needed if command parsing should live in the video layer instead of
`StateExecutor`.

Possible helper:

```python
def handle_image_command(self, message: str) -> bool:
    ...
```

Keep the public behavior precise:

- image show does not append idle image to playlist,
- image show does not trigger `videoEnd`,
- clear/default loads the configured `iddle_image`,
- video playback after an image still behaves normally and returns to idle after
  video end.

### Tests

#### [MODIFY] `raspberry_pi/tests/test_schema_validator.py`

Add tests that:

- accept `{"action": "image", "message": "SHOW:wallpaper.png"}`,
- accept `{"action": "image", "message": "CLEAR"}`,
- reject `{"action": "image", "message": "SHOW:"}`,
- reject `{"action": "image", "message": "wallpaper.png"}` because saved JSON
  must use `SHOW:<filename>`,
- reject missing/blank image message,
- reject unknown action typo such as `"photo"` if only `"image"` is canonical,
- reject non-image extensions in `image` action, for example `.mp4`, `.mp3`,
  `.wav`, and `.webm`.
- reject unsafe filenames such as `SHOW:../wallpaper.png`,
  `SHOW:/tmp/wallpaper.png`, and `SHOW:subdir/wallpaper.png`.
- reject non-string messages such as `{"action": "image", "message": true}`.

#### [MODIFY] `raspberry_pi/tests/test_video_handler_end_detection.py`

If image command parsing is added to `VideoHandler`, add direct tests that:

- `SHOW:<image>` calls/loads image without idle append,
- `CLEAR` returns to idle image,
- `SHOW:` without filename fails,
- bare filename fails for the dedicated image command parser,
- showing image does not fire `videoEnd`,
- video after image still fires `videoEnd` normally.

#### [ADD OR MODIFY] `raspberry_pi/tests/test_state_executor.py`

If there is no existing state executor test file, add a focused one with fake
handlers:

- `image SHOW:file.png` calls `show_image("file.png")`,
- `image CLEAR` and `image DEFAULT` call `stop_video()`,
- `image SHOW:` returns false and does not call `show_image`,
- `image file.png` returns false and does not call `show_image`,
- unsafe image paths return false and do not call `show_image`,
- unsupported command logs failure but does not crash.

### Current web dashboard editor

#### [MODIFY] `museum-dashboard/src/hooks/useSceneEditor.js`

- Add `image` as a valid action type in helper defaults and sanitation logic.
- Make `createEmptyAction('image')` produce:

```js
{ action: 'image', message: 'SHOW:' }
```

or, if the UI picks files directly:

```js
{ action: 'image', message: '' }
```

#### [MODIFY] `museum-dashboard/src/components/SceneEditor/ActionListEditor.jsx`

- Add `image` to `TYPE_LABELS`.
- Add `image` to `TYPE_CYCLE`:

```js
const TYPE_CYCLE = {
  mqtt: 'audio',
  audio: 'video',
  video: 'image',
  image: 'mqtt',
};
```

- Hide topic input for `image`, same as audio/video.
- Use image-specific placeholder:

```text
SHOW:wallpaper.png | CLEAR
```

#### [MODIFY] `museum-dashboard/src/components/SceneEditor/VisualTimeline.jsx`

- Add `image` to `TRACK_TYPES`.
- Filter image timeline items into their own row.

#### [MODIFY] `museum-dashboard/src/components/SceneEditor/TimelineTrack.jsx`

- Add `image` to `TRACK_LABELS`.
- Ensure drag/drop and row labels handle image actions.

#### [MODIFY] `museum-dashboard/src/components/SceneEditor/TimelineClip.jsx`

- Add `image` type label and compact display text.
- For image actions, show the `message` only, same as audio/video.

#### [MODIFY] `museum-dashboard/src/components/SceneEditor/ClipPopover.jsx`

- For `image`, show command/file field but no topic field.
- Placeholder should be `SHOW:wallpaper.png` or `CLEAR`.

#### [MODIFY] `museum-dashboard/src/components/SceneEditor/EditorPalette.jsx`

- Split uploaded media into video items and image items.
- Add an "Images" palette section.
- Image click inserts:

```js
onInsert(null, `SHOW:${imageName}`, 'image')
```

- Keep video click inserting existing `PLAY_VIDEO:<videoName>`.
- Do not save bare image filenames from the editor; always save
  `SHOW:<filename>` or `CLEAR`.
- Preview can still use the existing media preview/play route.

#### [MODIFY] `museum-dashboard/src/hooks/useDevicePalette.js`

- Split `videos` from `/api/media/video` into:
  - video-like extensions: `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm`
  - image-like extensions: `.png`, `.jpg`, `.jpeg`
- Return `imageItems` for the editor palette.

#### [MODIFY] `museum-dashboard/src/components/Scenes/SceneVisualizer.jsx`

- Render `image` actions as a first-class action type instead of falling through.
- Add a color/legend item only if the visualizer displays action type legends.

#### [MODIFY] `museum-dashboard/src/styles/theme.css`

- Add image badge variables, for example:

```css
--badge-image-color: ...
--badge-image-bg: ...
```

Avoid making the palette another purple/pink clone if video already uses that
color family.

#### [MODIFY] `museum-dashboard/src/styles/views/scene-editor-v2.css`

- Add `se2-action-badge--image`.
- Add `se2-tl-track-label--image`.
- Add `se2-tl-clip--image`.
- Add `se2-tl-popover-type--image`.

### Standalone SceneGen editor - SKIPPED

SKIPPED 2026-06-07: The user confirmed the standalone SceneGen app is no longer
used for production editing. It has been renamed to `SceneGen_DO_NOT_UPDATE` to
make that explicit. Do not add image-action support there.

The active implementation target is:

- Raspberry Pi backend under `raspberry_pi/`
- dashboard-integrated editor under `museum-dashboard/`

If a future offline-only workflow needs the standalone SceneGen again, create a
new dedicated TODO instead of reopening this image-action plan.

### Docs

#### [MODIFY] `docs/04_mqtt_protocol.md`

- Add `image` action to the scene JSON action table.
- Clarify that image action is local to Raspberry Pi and not MQTT.
- Add quick examples:

```json
{ "action": "image", "message": "SHOW:wallpaper.png" }
{ "action": "image", "message": "CLEAR" }
```

#### [MODIFY] `docs/06_scene_state_machine.md`

- Add `image` to supported action types.
- Add validation and runtime behavior notes.

#### [MODIFY] `docs/08_video_engine.md`

- Mention that the video engine owns static image display too.
- Clarify difference:
  - video action can still play video/image for compatibility,
  - image action is the clean scene JSON API for static images.

#### [MODIFY] `raspberry_pi/utils/info.md`

- Update module summary so future AI/code review knows `StateExecutor` supports
  an `image` action via `VideoHandler`.

---

## Edge cases

| Situation                                             | Expected behavior                                                                                                   |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Image file does not exist                             | Runtime logs error/warning, action returns false, scene continues unless later transition depends on something else |
| Unsupported extension                                 | Validation should catch obvious cases or runtime rejects it                                                         |
| `SHOW:` without filename                            | Validator rejects it explicitly before runtime                                                                      |
| Bare filename in `image` action                     | Validator rejects it; editor should save `SHOW:<filename>` instead                                                |
| `SHOW:../image.png` or subdirectory path            | Validator rejects it; room/media folder comes from config                                                           |
| `CLEAR` while a video is playing                    | Video is interrupted and default image is loaded; do not fire `videoEnd` for the interrupted video                |
| `SHOW` while a video is playing                     | Video is replaced by image; do not fire `videoEnd` for the interrupted video                                      |
| Video starts after image                              | Video plays normally, appends idle image, and can trigger `videoEnd`                                              |
| Scene ends while image is displayed                   | The outer runtime service / stop coordinator calls `stop_video()`, returning to configured default image          |
| `video_handler` failed to initialize                | Image action logs simulation/no-handler warning; scene does not crash                                               |
| User sets default image to non-black                  | `CLEAR` uses configured `iddle_image`, not hardcoded `black.png`                                              |
| Existing scenes use `action: "video"` with `.png` | Keep working for backward compatibility                                                                             |
| Frontend loads an older scene without image actions   | No UI regression                                                                                                    |
| Frontend loads a new scene with image action          | It must render/edit/save without stripping action type                                                              |

---

## Implementation order

### Phase 1 - Backend contract - DONE 2026-06-09

1. Update `schema_validator.py` to accept and validate `image`.
2. Add `_execute_image()` to `state_executor.py`.
3. Add a shared `image_command.py` parser used by validation and runtime.
4. Keep all existing `video` image behavior for compatibility.
5. Keep `image` action strict: only `SHOW:<filename>` and clear/default aliases are
   accepted in saved scene JSON.

Acceptance:

- Existing scenes validate unchanged.
- New scene with image actions validates.
- No new dependency is introduced.

Completion note 2026-06-09:

- Added strict shared parser in `raspberry_pi/utils/image_command.py`.
- Added `image` schema support in `schema_validator.py`.
- Added runtime dispatch in `state_executor.py`.
- Kept legacy `video` image behavior unchanged.

### Phase 2 - Runtime tests - DONE 2026-06-09

1. Add schema validation tests for image actions.
2. Add state executor tests with a fake video handler.
3. Add or extend video handler tests if parsing is placed in `VideoHandler`.
4. Run safe backend tests on the Raspberry Pi:

```bash
cd ~/Documents/GitHub/museum-system/raspberry_pi
source venv/bin/activate
python3 tests/run_safe_tests.py
```

Acceptance:

- Safe tests pass.
- Image action show/clear is covered.
- Existing video end detection tests still pass.

Progress note 2026-06-09:

- Added schema validator tests for valid/invalid image actions.
- Added `raspberry_pi/tests/test_state_executor.py` for image show/clear/error
  dispatch.
- Did not add VideoHandler parser tests because parsing lives in
  `image_command.py` and `StateExecutor`, not in `VideoHandler`.
- Local `py_compile` passed for changed Python files.
- Direct local execution of the new state executor test functions passed
  (`9 passed`).
- Added `raspberry_pi/tests/conftest.py` and `pythonpath = .` in
  `raspberry_pi/pytest.ini` so Pi pytest runs can import `utils` reliably.
- Raspberry Pi targeted pytest passed on 2026-06-09:
  `pytest tests/test_schema_validator.py tests/test_state_executor.py`
  collected 35 items and passed all 35.
- Raspberry Pi safe runner passed on 2026-06-09:
  `python tests/run_safe_tests.py` ran the quick pytest suite and passed
  all 67 tests.

### Phase 3 - Current dashboard editor - DONE 2026-06-09

1. Add `image` action support to `useSceneEditor.js`.
2. Add image badge/type cycle to action rows.
3. Add image timeline track.
4. Add image clip/popover editing.
5. Split media palette into videos and images.
6. Normalize image file picks to `SHOW:<filename>` before saving.
7. Add image-specific CSS variables/classes.
8. Build dashboard:

```bash
cd museum-dashboard
npm run build
```

Acceptance:

- Editor can add an image action in `onEnter`, `timeline`, and `onExit`.
- Editor can add clear/default image command.
- Existing audio/video/MQTT editing still works.
- Built assets can be copied/served as usual.

Completion note 2026-06-09:

- Added `image` action defaults and export cleanup in `useSceneEditor.js`.
- Split video media from image media in `useDevicePalette.js`.
- Added image palette section, image action rows, timeline track/clip/popover
  support, and visualizer formatting.
- Added image badge/track/clip CSS variables and classes.
- Built dashboard with `npm run build`; generated `raspberry_pi/Web/dist`
  assets were updated.

### Phase 4 - Standalone SceneGen compatibility - SKIPPED

SKIPPED 2026-06-07: Standalone SceneGen is no longer used and is now named
`SceneGen_DO_NOT_UPDATE`.

Acceptance:

- No files under `SceneGen_DO_NOT_UPDATE/` are modified for this feature.
- Image action support is implemented only in the Raspberry Pi backend and the
  dashboard-integrated editor.

### Phase 5 - Documentation and manual verification - DONE 2026-06-12

1. Update MQTT/scene/video docs listed above.
2. Add a tiny manual scene file if useful, for example
   `raspberry_pi/scenes/room1/Image_TEST.json`.
3. On Raspberry Pi:
   - run safe tests,
   - restart service,
   - run the image test scene from dashboard,
   - verify show image,
   - verify clear/default image,
   - verify video still returns to default after ending.

Acceptance:

- The display shows the selected image indefinitely.
- `CLEAR` returns to configured idle/default image.
- Starting a normal video after image still works.
- Stopping or ending a scene returns to default image.

Progress note 2026-06-09:

- Updated `docs/04_mqtt_protocol.md`, `docs/06_scene_state_machine.md`,
  `docs/08_video_engine.md`, and `raspberry_pi/utils/info.md`.
- Added `raspberry_pi/scenes/room1/Image_TEST.json` for manual display
  verification on the default room.
- Raspberry Pi safe tests passed on 2026-06-09:
  `python tests/run_safe_tests.py` passed all 67 tests.
- Manual Raspberry Pi show-image check passed: the selected image displays
  properly.
- Full end-to-end Raspberry Pi verification of the current `Image_TEST.json`
  passed on 2026-06-12. The BP defense scene works on the Pi after the later
  timing/content changes: Obhajoba images, relay sequence, OHEN video/audio/fire
  synchronization, and final cleanup/default return are accepted for closure.

---

## Open decisions before implementation

1. Should clear aliases be kept?
   - decided: keep `CLEAR` canonical and accept `DEFAULT`; do not accept
     `BLACK` because the configured idle image may not be black.
2. Should image actions appear on their own timeline row?
   - decided: yes, because it keeps video and image intent visually clear.
3. Should standalone SceneGen be updated or skipped?
   - decided 2026-06-07: skipped. Standalone SceneGen is no longer used and was
     renamed to `SceneGen_DO_NOT_UPDATE`.

## Not in scope

- Image duration parameter.
- Fade/transition effects between images.
- Cropping/fitting modes.
- Slideshow/playlist behavior.
- Separate image process outside mpv.
- MQTT topic for image display. This is a local scene action, just like audio
  and video actions.
