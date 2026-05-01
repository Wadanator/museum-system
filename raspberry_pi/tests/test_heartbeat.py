import configparser
import os
import sys
import time
import threading
import tempfile
from pathlib import Path

RPI_DIR = Path(__file__).resolve().parents[1]
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

import main as main_module
from main import MuseumController

import watchdog as watchdog_module
from watchdog import MuseumWatchdog, _SCENE_STATE_STALE_SECONDS


class _FailOnWrite:
    """Path substitute whose write_text always raises OSError."""
    def write_text(self, *a, **kw):
        raise OSError("simulated disk error")


def _build_controller(scene_running: bool = False, heartbeat_interval: float = 0.05):
    c = MuseumController.__new__(MuseumController)
    c.scene_lock = threading.Lock()
    c.scene_running = scene_running
    c.room_id = 'room1'
    c.scene_parser = None
    c.audio_handler = None
    c.video_handler = None
    c.web_dashboard = None
    c.actuator_state_store = None
    c.scene_heartbeat_interval = heartbeat_interval
    c._heartbeat_stop_event = threading.Event()
    c._heartbeat_thread = None
    return c


def _build_watchdog():
    wd = MuseumWatchdog.__new__(MuseumWatchdog)
    wd.scene_wait_poll_interval = 30
    wd.scene_wait_max_seconds = 7200
    return wd


# ── Heartbeat tests ───────────────────────────────────────────────────────────

def test_heartbeat_refreshes_mtime_while_scene_running():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller()

            c._set_scene_running(True, 'start', expect_current=False)
            mtime_before = state_file.stat().st_mtime

            time.sleep(0.35)  # ~7 heartbeat cycles at 0.05 s

            mtime_after = state_file.stat().st_mtime
            assert mtime_after > mtime_before, "mtime must advance while scene runs"
        finally:
            c._set_scene_running(False, 'stop')
            main_module._SCENE_STATE_FILE = original


def test_heartbeat_stops_when_scene_ends():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller()

            c._set_scene_running(True, 'start', expect_current=False)
            time.sleep(0.15)
            c._set_scene_running(False, 'stop')

            assert state_file.read_text() == 'idle'
            mtime_at_stop = state_file.stat().st_mtime

            time.sleep(0.3)

            assert state_file.stat().st_mtime == mtime_at_stop, "mtime must not advance after stop"
            assert state_file.read_text() == 'idle'
        finally:
            main_module._SCENE_STATE_FILE = original


def test_heartbeat_thread_is_daemon():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller()

            c._set_scene_running(True, 'start', expect_current=False)
            assert c._heartbeat_thread is not None
            assert c._heartbeat_thread.daemon is True
        finally:
            c._set_scene_running(False, 'stop')
            main_module._SCENE_STATE_FILE = original


def test_heartbeat_double_start_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller()

            c._set_scene_running(True, 'start', expect_current=False)
            first_thread = c._heartbeat_thread

            c._set_scene_running(True, 'duplicate')  # no-op, returns False
            assert c._heartbeat_thread is first_thread
        finally:
            c._set_scene_running(False, 'stop')
            main_module._SCENE_STATE_FILE = original


def test_heartbeat_double_stop_is_safe():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller()

            c._set_scene_running(True, 'start', expect_current=False)
            c._set_scene_running(False, 'stop_scene_path')  # transitions, stops heartbeat
            c._set_scene_running(False, 'finally_path')    # no-op — must not raise

            assert c._heartbeat_thread is None
            assert state_file.read_text() == 'idle'
        finally:
            main_module._SCENE_STATE_FILE = original


def test_heartbeat_join_is_fast():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller(heartbeat_interval=0.05)

            c._set_scene_running(True, 'start', expect_current=False)

            t0 = time.monotonic()
            c._set_scene_running(False, 'stop')
            elapsed = time.monotonic() - t0

            assert elapsed < 0.5, f"stop took {elapsed:.3f}s — Event.wait must wake immediately on set()"
        finally:
            main_module._SCENE_STATE_FILE = original


def test_heartbeat_survives_oserror_on_write():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller(heartbeat_interval=0.05)

            c._set_scene_running(True, 'start', expect_current=False)

            # Replace state file with one that always raises OSError on write
            main_module._SCENE_STATE_FILE = _FailOnWrite()
            time.sleep(0.25)  # several cycles fail

            assert c._heartbeat_thread is not None
            assert c._heartbeat_thread.is_alive(), "OSError must not kill heartbeat thread"
        finally:
            main_module._SCENE_STATE_FILE = state_file
            c._set_scene_running(False, 'stop')
            main_module._SCENE_STATE_FILE = original


def test_stale_running_not_written_after_scene_stops():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = main_module._SCENE_STATE_FILE
        try:
            main_module._SCENE_STATE_FILE = state_file
            c = _build_controller(heartbeat_interval=0.05)

            c._set_scene_running(True, 'start', expect_current=False)
            time.sleep(0.1)
            c._set_scene_running(False, 'stop')

            assert state_file.read_text() == 'idle'
            time.sleep(0.3)
            assert state_file.read_text() == 'idle', "heartbeat must not overwrite 'idle' with 'running'"
        finally:
            main_module._SCENE_STATE_FILE = original


# ── Watchdog stale-detection tests ───────────────────────────────────────────

def test_watchdog_stale_file_is_treated_as_idle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = watchdog_module._SCENE_STATE_FILE
        try:
            watchdog_module._SCENE_STATE_FILE = state_file
            state_file.write_text('running')
            old_mtime = time.time() - (_SCENE_STATE_STALE_SECONDS + 1)
            os.utime(state_file, (old_mtime, old_mtime))

            wd = _build_watchdog()
            assert wd._is_scene_running() is False
        finally:
            watchdog_module._SCENE_STATE_FILE = original


def test_watchdog_fresh_running_file_is_detected():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = watchdog_module._SCENE_STATE_FILE
        try:
            watchdog_module._SCENE_STATE_FILE = state_file
            state_file.write_text('running')

            wd = _build_watchdog()
            assert wd._is_scene_running() is True
        finally:
            watchdog_module._SCENE_STATE_FILE = original


def test_watchdog_idle_file_is_not_running():
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_file = Path(tmp_dir) / 'museum_scene_state'
        original = watchdog_module._SCENE_STATE_FILE
        try:
            watchdog_module._SCENE_STATE_FILE = state_file
            state_file.write_text('idle')

            wd = _build_watchdog()
            assert wd._is_scene_running() is False
        finally:
            watchdog_module._SCENE_STATE_FILE = original


def test_watchdog_init_reads_scene_wait_values_from_config():
    """MuseumWatchdog.__init__ must actually set attributes from _config_manager.config."""
    import shutil
    from utils.config_manager import ConfigManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        example = RPI_DIR / 'config' / 'config.ini.example'
        cfg_file = Path(tmp_dir) / 'config.ini'
        shutil.copy(str(example), str(cfg_file))

        cfg = configparser.ConfigParser()
        cfg.read(str(cfg_file))
        cfg.set('System', 'scene_wait_max_seconds', '9000')
        cfg.set('System', 'scene_wait_poll_interval', '45')
        with open(str(cfg_file), 'w') as fh:
            cfg.write(fh)

        cm = ConfigManager(config_file=str(cfg_file))
        original_cm = watchdog_module._config_manager
        watchdog_module._config_manager = cm
        try:
            wd = MuseumWatchdog()
            assert wd.scene_wait_max_seconds == 9000
            assert wd.scene_wait_poll_interval == 45
        finally:
            watchdog_module._config_manager = original_cm


def test_watchdog_init_clamps_zero_poll_interval():
    """scene_wait_poll_interval = 0 must be clamped to 1 to prevent a tight loop."""
    import shutil
    from utils.config_manager import ConfigManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        example = RPI_DIR / 'config' / 'config.ini.example'
        cfg_file = Path(tmp_dir) / 'config.ini'
        shutil.copy(str(example), str(cfg_file))

        cfg = configparser.ConfigParser()
        cfg.read(str(cfg_file))
        cfg.set('System', 'scene_wait_poll_interval', '0')
        with open(str(cfg_file), 'w') as fh:
            cfg.write(fh)

        cm = ConfigManager(config_file=str(cfg_file))
        original_cm = watchdog_module._config_manager
        watchdog_module._config_manager = cm
        try:
            wd = MuseumWatchdog()
            assert wd.scene_wait_poll_interval >= 1
        finally:
            watchdog_module._config_manager = original_cm
