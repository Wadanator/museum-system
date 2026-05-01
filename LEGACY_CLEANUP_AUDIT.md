# Legacy Cleanup Audit

Date: 2026-05-02

Scope:
- `raspberry_pi/` backend, services, scenes, dashboard backend
- `museum-dashboard/src/` React dashboard source
- selected repository-level docs that still describe old files

This document does not delete anything. It records historical or generated files that should be cleaned up later, with risk notes.

## Summary

The active production path is now:

- Raspberry Pi runtime: `raspberry_pi/main.py`
- Service initialization: `raspberry_pi/utils/service_container.py`
- Scene execution: state-machine JSON via `StateMachine`, `SceneParser`, `StateExecutor`, `TransitionManager`
- Web API: `raspberry_pi/Web/routes/api.py`
- Dashboard source: `museum-dashboard/src/`
- Built production dashboard: `raspberry_pi/Web/dist/`

The repository still contains a few older artifacts from previous iterations:

- old timestamp-list `room2` scenes
- duplicate/obsolete dashboard components
- editor temp scripts
- empty placeholder files
- generated Python caches
- docs that still list old file structure

## Safe Cleanup Candidates

These appear safe to remove after one final `rg` check. They are not part of the current runtime path.

### `raspberry_pi/Web/handlers/route_handler.py`

Status: tracked file, currently empty.

Evidence:
- File length is `0`.
- No active import found outside documentation.
- Flask blueprints are registered through `raspberry_pi/Web/app.py` and `raspberry_pi/Web/routes/api.py`.

Recommendation:
- Delete this file.
- Remove it from `docs/03_file_structure.md`.

Risk:
- Very low. It has no content and no runtime references.

### `raspberry_pi/tempCodeRunnerFile.sh`

Status: tracked file, editor/runner artifact.

Evidence:
- Name matches VS Code temporary runner output.
- Not referenced by install scripts or runtime.
- Listed in `docs/03_file_structure.md`, which likely captured it accidentally.

Recommendation:
- Delete this file.
- Remove it from `docs/03_file_structure.md`.

Risk:
- Very low.

### `raspberry_pi/services/tempCodeRunnerFile.sh`

Status: tracked file, editor/runner artifact.

Evidence:
- Contains ad-hoc service stop/start commands.
- Not used by `install.sh` or `install_offline.sh`.
- Production service templates are `museum.service.template` and `museum-watchdog.service.template`.

Recommendation:
- Delete this file.
- Remove it from `docs/03_file_structure.md`.

Risk:
- Very low. If a manual restart helper is desired, create a clearly named script such as `restart_services_dev.sh`.

### `museum-dashboard/src/App.css`

Status: tracked file, currently empty.

Evidence:
- File length is `0`.
- No active import found in current `App.jsx`.
- Styling is now centralized under `src/styles/`.

Recommendation:
- Delete this file.
- Remove it from docs.

Risk:
- Very low.

### `raspberry_pi/**/__pycache__/` and `*.pyc`

Status: generated runtime/build artifacts, not tracked by Git in this local check.

Evidence:
- Present under `raspberry_pi/`, `utils/`, `Web/`, `tests/`, and subpackages.
- `git ls-files "*__pycache__*" "*.pyc"` returned no tracked files.

Recommendation:
- Delete local caches before packaging or release.
- Ensure `.gitignore` excludes `__pycache__/` and `*.pyc`.

Risk:
- None for source code. Python regenerates these automatically.

### Root `tmp*` directories

Observed:
- `tmp04_vc3p2`
- `tmp94ybefz2`
- `tmpwzflqskk`

Evidence:
- They caused access-denied warnings during `rg` and `git status`.
- They look like local temporary directories, not project source.

Recommendation:
- Inspect ownership/contents manually on Windows.
- Delete only after confirming they are not opened by another process.
- Add an ignore rule for local temp directories if they recur.

Risk:
- Unknown until inspected because access is denied from this shell.

## Likely Legacy, But Verify Before Deleting

These are probably historical, but deletion could affect manual workflows or archived demos.

### `museum-dashboard/src/components/Dashboard/DashboardControls.jsx`

Status: tracked, not imported by current dashboard source.

Evidence:
- `MainDashboard.jsx` currently uses `HeroCard`.
- No active import of `DashboardControls` found outside built assets/docs.
- Its UI duplicates the run/stop control now implemented inside `HeroCard`.

Recommendation:
- Delete if no branch or pending UI refactor still uses it.

Risk:
- Low for current app.
- If someone planned to split `HeroCard` again into smaller pieces, archive the file content first or recreate from Git history.

### `museum-dashboard/src/components/Dashboard/BigStatusCard.jsx`

Status: tracked, not imported by current dashboard source.

Evidence:
- `MainDashboard.jsx` uses `HeroCard`.
- `BigStatusCard` duplicates the status half of `HeroCard`.
- No active import found outside built assets/docs.

Recommendation:
- Delete together with `DashboardControls.jsx`.

Risk:
- Low for current app.

### `museum-dashboard/src/index.css`

Status: tracked, empty, still imported by `museum-dashboard/src/main.jsx`.

Evidence:
- File length is `0`.
- `main.jsx` imports it before the real style files.

Recommendation:
- Either keep it as an intentional Vite placeholder, or remove the import and delete the file.
- If deleted, verify `npm run build`.

Risk:
- Very low, but requires removing the import too.

### `raspberry_pi/scenes/room2/intro.json`

Status: tracked scene file in old timestamp-list format.

Evidence:
- File is a JSON array of `{timestamp, topic, message}` actions.
- Current engine requires a state-machine object with `sceneId`, `initialState`, and `states`.
- Current configured room is `room1`.

Recommendation:
- If `room2` is no longer used, archive or delete the whole `raspberry_pi/scenes/room2/` folder.
- If `room2` is still planned, convert the scenes to the current state-machine schema before use.

Risk:
- Medium only if `room2` is still used for demos or future multi-room work.

### `raspberry_pi/scenes/room2/test.json`

Status: tracked scene file in old timestamp-list format.

Evidence:
- Same old format as `room2/intro.json`.
- Contains old topics such as `room2/audio`, `room2/video`, `room2/motor`.
- Not loadable by the current schema validator as a modern scene.

Recommendation:
- Same as `room2/intro.json`: delete/archive if room2 is obsolete, or convert if room2 will return.

Risk:
- Medium only for future `room2` use.

### `raspberry_pi/scenes/room1/devices.json`

Status: tracked legacy devices config location.

Evidence:
- Current preferred location is `raspberry_pi/config/rooms/room1/devices.json`.
- `raspberry_pi/Web/routes/commands.py` still contains a legacy fallback that migrates from `scenes/<room>/devices.json` if the new file is missing.
- The dashboard hides `devices.json` from the scene list.

Recommendation:
- Keep temporarily if you want rollback compatibility.
- Delete after confirming the Pi and web dashboard consistently use `config/rooms/room1/devices.json`.
- After deletion, keep the fallback for one or two releases, then remove the fallback too if no old deployments remain.

Risk:
- Medium if somebody still manually edits the old file.

## Keep For Now

These look old at first glance, but should not be deleted casually.

### `raspberry_pi/Web/routes/__init__.py`

Status: empty package marker.

Recommendation:
- Keep unless the project intentionally moves to namespace packages everywhere.

Risk if deleted:
- Low on modern Python, but unnecessary churn.

### `raspberry_pi/Web/utils/__init__.py`

Status: empty package marker.

Recommendation:
- Keep for consistency.

### `raspberry_pi/Web/handlers/__init__.py`

Status: empty package marker.

Recommendation:
- Keep for consistency.

### `raspberry_pi/Web/dist/`

Status: tracked production frontend build output.

Evidence:
- Flask serves built assets from `raspberry_pi/Web/dist`.
- `museum-dashboard/vite.config.js` now builds directly to `../raspberry_pi/Web/dist`.

Recommendation:
- Keep if the Raspberry Pi deploy flow expects the built dashboard to be present without running `npm build` on the Pi.
- If switching to a source-only repo later, document the build step and remove `dist` from Git in one deliberate change.

Risk if deleted:
- High unless deploy scripts are updated to build frontend before starting Flask.

### `iddle_image`

Status: misspelled but active compatibility key.

Evidence:
- Used consistently in config, `ConfigManager`, `ServiceContainer`, and `VideoHandler`.

Recommendation:
- Do not rename casually.
- If desired, add support for both `idle_image` and `iddle_image` later, then migrate config gradually.

Risk if renamed directly:
- Medium. Existing configs would break.

## Documentation Drift

### `docs/03_file_structure.md`

Status: outdated in places.

Evidence:
- Lists `route_handler.py`.
- Lists `tempCodeRunnerFile.sh`.
- Lists empty/legacy frontend files as normal structure.
- Does not fully reflect newer config layout under `raspberry_pi/config/rooms/`.

Recommendation:
- Update after cleanup, not before.
- Treat as documentation drift rather than runtime risk.

## Suggested Cleanup Order

1. Delete editor/runtime artifacts:
   - `raspberry_pi/tempCodeRunnerFile.sh`
   - `raspberry_pi/services/tempCodeRunnerFile.sh`
   - local `__pycache__/`
   - local root `tmp*` directories after manual inspection

2. Delete empty or unused source placeholders:
   - `raspberry_pi/Web/handlers/route_handler.py`
   - `museum-dashboard/src/App.css`
   - optionally `museum-dashboard/src/index.css` plus its import

3. Delete obsolete frontend components:
   - `DashboardControls.jsx`
   - `BigStatusCard.jsx`

4. Decide on legacy data:
   - `raspberry_pi/scenes/room2/*`
   - `raspberry_pi/scenes/room1/devices.json`

5. Update documentation:
   - `docs/03_file_structure.md`

6. Run checks:
   - frontend build after frontend cleanup
   - Python compile after backend cleanup
   - manual web smoke test on Raspberry Pi

