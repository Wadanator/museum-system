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

### ~~`raspberry_pi/Web/handlers/route_handler.py`~~ ✓ DONE

Deleted. Empty file with no runtime references. Removed from `docs/03_file_structure.md`.

### ~~`raspberry_pi/tempCodeRunnerFile.sh`~~ ✓ DONE

Deleted. VS Code runner artifact, not used by install or runtime. Removed from `docs/03_file_structure.md`.

### ~~`raspberry_pi/services/tempCodeRunnerFile.sh`~~ ✓ DONE

Deleted. Same editor artifact with ad-hoc service commands. Removed from `docs/03_file_structure.md`.

### ~~`museum-dashboard/src/App.css`~~ ✓ DONE

Deleted. Empty file, not imported anywhere. Styling is in `src/styles/`. Removed from `docs/03_file_structure.md`.

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

### ~~`museum-dashboard/src/components/Dashboard/DashboardControls.jsx`~~ ✓ DONE

Deleted. Not imported anywhere in the current dashboard. UI duplicated controls now inside `HeroCard`.

### ~~`museum-dashboard/src/components/Dashboard/BigStatusCard.jsx`~~ ✓ DONE

Deleted. Not imported anywhere. Status display is now part of `HeroCard`.

### ~~`museum-dashboard/src/index.css`~~ ✓ DONE

Deleted. Empty file. Import removed from `main.jsx`. Removed from `docs/03_file_structure.md`.

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

Status: updated after LOW-risk cleanup (2026-05-15). Still needs a pass for newer config layout under `raspberry_pi/config/rooms/`.

## Suggested Cleanup Order

1. ~~Delete editor/runtime artifacts~~ ✓ DONE
   - ~~`raspberry_pi/tempCodeRunnerFile.sh`~~
   - ~~`raspberry_pi/services/tempCodeRunnerFile.sh`~~
   - local `__pycache__/`
   - local root `tmp*` directories after manual inspection

2. ~~Delete empty or unused source placeholders~~ ✓ DONE
   - ~~`raspberry_pi/Web/handlers/route_handler.py`~~
   - ~~`museum-dashboard/src/App.css`~~
   - ~~`museum-dashboard/src/index.css` plus its import~~

3. ~~Delete obsolete frontend components~~ ✓ DONE
   - ~~`DashboardControls.jsx`~~
   - ~~`BigStatusCard.jsx`~~

4. Decide on legacy data:
   - `raspberry_pi/scenes/room2/*`
   - `raspberry_pi/scenes/room1/devices.json`

5. Update documentation:
   - `docs/03_file_structure.md` — partial, needs config/rooms section

6. Run checks:
   - frontend build after frontend cleanup
   - Python compile after backend cleanup
   - manual web smoke test on Raspberry Pi
