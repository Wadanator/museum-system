#!/usr/bin/env python3
"""
System watchdog for the Museum System.

Monitors the museum-system service and restarts it when health checks fail.
Enhanced with scene-aware restart logic — never interrupts a running
presentation — and audio-error tolerance to avoid false-positive restarts.
"""

import os
import sys
import time
import subprocess
import psutil
import logging
from pathlib import Path

# Allow imports from raspberry_pi/ root (same as main.py)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from utils.config_manager import ConfigManager
from utils.logging_setup import setup_logging_from_config, get_logger

_config_manager = ConfigManager()
setup_logging_from_config(_config_manager.get_logging_config())
log = get_logger('watchdog')

# Resolve paths relative to this file — never hardcode absolute paths.
# watchdog.py lives in raspberry_pi/, so parent == raspberry_pi/.
_BASE_DIR = Path(__file__).resolve().parent
_LOG_FILE = _BASE_DIR / 'logs' / 'museum.log'

# Written by main.py when a scene starts/ends.
# Watchdog reads this before deciding to restart.
_SCENE_STATE_FILE = Path('/tmp/museum_scene_state')


class MuseumWatchdog:
    """
    Monitors the museum-system systemd service and restarts it when needed.

    Key behaviours
    --------------
    - Tolerates temporary CPU spikes caused by audio initialisation failures.
    - Waits for the current scene to finish before restarting the service.
    - Caps restarts at max_restarts_per_hour to prevent restart loops.
    """

    def __init__(self) -> None:
        self.service_name: str = 'museum-system'
        self.check_interval: int = 60

        # Resource thresholds
        self.max_memory_mb: int = 1024
        self.max_cpu_percent: float = 85.0
        self.cpu_spike_tolerance: int = 3      # consecutive high-CPU readings before restart
        self.high_cpu_count: int = 0

        # Restart rate limiting
        self.restart_count: int = 0
        self.max_restarts_per_hour: int = 5
        self.consecutive_failures: int = 0
        self.max_consecutive_failures: int = 3

        # Audio-error grace period — high CPU right after an audio error is expected
        self.audio_error_restart_delay: int = 300   # seconds
        self.last_audio_error_time: float = 0.0

        # Scene-aware restart: poll interval and hard timeout while waiting
        self.scene_wait_poll_interval: int = 30     # seconds between state checks
        self.scene_wait_max_seconds: int = 3600     # give up after 1 hour

    # ------------------------------------------------------------------
    # Scene state helpers
    # ------------------------------------------------------------------

    def _is_scene_running(self) -> bool:
        """
        Return True if a scene is currently active.

        Reads /tmp/museum_scene_state written by main.py.
        A file older than two hours is treated as stale — main.py likely
        crashed without writing 'idle', so restarting is safe.
        """
        if not _SCENE_STATE_FILE.exists():
            return False

        try:
            age = time.time() - _SCENE_STATE_FILE.stat().st_mtime
            if age > 7200:
                log.debug('Scene state file is %.0fs old — treating as idle', age)
                return False

            return _SCENE_STATE_FILE.read_text().strip() == 'running'

        except OSError as e:
            log.debug('Could not read scene state file: %s', e)
            return False

    def _wait_for_scene_to_finish(self) -> None:
        """
        Block until the running scene finishes or the hard timeout elapses.

        Logs progress every poll interval so operators can follow along
        in the watchdog log without being flooded with messages.
        """
        log.warning(
            'Scene is running — waiting up to %ds before restart.',
            self.scene_wait_max_seconds,
        )
        waited = 0

        while waited < self.scene_wait_max_seconds:
            time.sleep(self.scene_wait_poll_interval)
            waited += self.scene_wait_poll_interval

            if not self._is_scene_running():
                log.info('Scene finished after %ds — proceeding with restart.', waited)
                return

            log.info('Scene still running (%ds elapsed) — waiting...', waited)

        log.error(
            'Scene still running after %ds hard timeout — forcing restart.',
            self.scene_wait_max_seconds,
        )

    # ------------------------------------------------------------------
    # Service / process inspection
    # ------------------------------------------------------------------

    def is_service_running(self) -> bool:
        """Return True if the systemd service reports as active."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip() == 'active'
        except Exception as e:
            log.error('Error checking service status: %s', e)
            return False

    def get_service_process(self) -> 'psutil.Process | None':
        """Return the psutil.Process for main.py, or None if not found."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    return proc
        except Exception:
            pass
        return None

    def check_recent_logs_for_audio_errors(self) -> bool:
        """
        Return True if the log file contains recent audio-init errors.

        Reads only the last 64 KB so this stays fast even on large log files.
        Sets self.last_audio_error_time so callers can implement grace periods.
        """
        if not _LOG_FILE.exists():
            return False

        try:
            with open(_LOG_FILE, 'rb') as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 64 * 1024))
                tail = f.read().decode('utf-8', errors='ignore')

            audio_error_patterns = [
                'Error initializing pygame mixer',
                "ALSA: Couldn't open audio device",
                'Audio initialization failed',
                'Audio permanently disabled',
            ]

            for pattern in audio_error_patterns:
                if pattern in tail:
                    self.last_audio_error_time = time.time()
                    return True

        except OSError as e:
            log.debug('Could not read log file: %s', e)

        return False

    def check_process_health(self) -> tuple[bool, str]:
        """
        Inspect memory and CPU usage of the running process.

        Returns
        -------
        (healthy, status_message)
        """
        proc = self.get_service_process()
        if not proc:
            self.consecutive_failures += 1
            return False, 'Process not found'

        try:
            self.consecutive_failures = 0

            memory_mb = proc.memory_info().rss / 1024 / 1024
            if memory_mb > self.max_memory_mb:
                return (
                    False,
                    f'High memory usage: {memory_mb:.1f}MB (limit: {self.max_memory_mb}MB)',
                )

            cpu_percent = proc.cpu_percent(interval=1)

            if cpu_percent > self.max_cpu_percent:
                self.high_cpu_count += 1

                # Audio init can cause a temporary CPU spike — be tolerant
                is_audio_error_period = (
                    (time.time() - self.last_audio_error_time) < 120
                )

                if self.high_cpu_count >= self.cpu_spike_tolerance:
                    if is_audio_error_period or self.check_recent_logs_for_audio_errors():
                        if (time.time() - self.last_audio_error_time) < self.audio_error_restart_delay:
                            log.warning(
                                'High CPU (%.1f%%) likely due to audio issues — delaying restart.',
                                cpu_percent,
                            )
                            return True, f'High CPU (audio-related): {cpu_percent:.1f}% - monitoring'
                        return False, f'Persistent high CPU after audio errors: {cpu_percent:.1f}%'

                    return False, f'High CPU usage: {cpu_percent:.1f}% (consecutive: {self.high_cpu_count})'
            else:
                self.high_cpu_count = 0

            return True, f'Healthy - CPU: {cpu_percent:.1f}%, Memory: {memory_mb:.1f}MB'

        except Exception as e:
            return False, f'Error checking health: {e}'

    # ------------------------------------------------------------------
    # Restart decision and execution
    # ------------------------------------------------------------------

    def should_restart_service(self, reason: str) -> bool:
        """
        Return True if conditions allow a service restart right now.

        Checks rate limits, consecutive-failure thresholds, and the
        audio-error grace period before approving a restart.
        Scene awareness is handled separately in restart_service().
        """
        if self.restart_count >= self.max_restarts_per_hour:
            log.error(
                'Restart limit reached (%d/hour) — manual intervention required.',
                self.max_restarts_per_hour,
            )
            return False

        if 'Process not found' in reason:
            if self.consecutive_failures < self.max_consecutive_failures:
                log.warning(
                    'Process not found (%d/%d) — monitoring...',
                    self.consecutive_failures,
                    self.max_consecutive_failures,
                )
                return False

        if 'audio' in reason.lower() or self.check_recent_logs_for_audio_errors():
            if (time.time() - self.last_audio_error_time) < self.audio_error_restart_delay:
                log.warning(
                    'Audio-related issue — waiting %ds before restart.',
                    self.audio_error_restart_delay,
                )
                return False

        return True

    def restart_service(self, reason: str) -> bool:
        """
        Stop and start the systemd service.

        Waits for any running scene to finish first so a live museum
        presentation is never interrupted mid-playback.
        """
        if not self.should_restart_service(reason):
            return False

        # Scene-aware restart: never kill a running presentation
        if self._is_scene_running():
            self._wait_for_scene_to_finish()

        self.restart_count += 1
        log.warning('Restarting service (#%d) — Reason: %s', self.restart_count, reason)

        try:
            log.info('Attempting graceful service stop...')
            subprocess.run(
                ['sudo', 'systemctl', 'stop', self.service_name],
                capture_output=True, check=False, timeout=30,
            )
            time.sleep(10)

            # Force-kill if the process is still alive
            proc = self.get_service_process()
            if proc:
                log.warning('Process still running — forcing termination.')
                try:
                    proc.terminate()
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
                time.sleep(5)

            subprocess.run(
                ['sudo', 'systemctl', 'daemon-reload'],
                capture_output=True, check=False, timeout=10,
            )
            time.sleep(2)

            subprocess.run(
                ['sudo', 'systemctl', 'start', self.service_name],
                capture_output=True, check=True, timeout=30,
            )
            log.info('Service restarted successfully.')

            self.high_cpu_count = 0
            self.consecutive_failures = 0

            # Clear stale state file — main.py will recreate it on next scene
            try:
                _SCENE_STATE_FILE.unlink(missing_ok=True)
            except OSError:
                pass

            return True

        except subprocess.CalledProcessError as e:
            log.error('Failed to restart service: %s', e)
            return False
        except Exception as e:
            log.error('Unexpected error during restart: %s', e)
            return False

    # ------------------------------------------------------------------
    # Connectivity check
    # ------------------------------------------------------------------

    def check_web_interface(self) -> bool:
        """Return True if the web dashboard responds on port 5000."""
        try:
            import requests
            response = requests.get('http://localhost:5000', timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_network_connectivity(self) -> bool:
        """Return True if the external network is reachable."""
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '8.8.8.8'],
                capture_output=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the watchdog monitoring loop indefinitely."""
        log.info('Museum System Watchdog started.')

        network_down_logged = False
        startup_complete = False
        loop_count = 0
        last_restart_count_reset = time.time()

        while True:
            try:
                loop_count += 1
                current_time = time.time()

                # Reset hourly restart counter
                if current_time - last_restart_count_reset > 3600:
                    self.restart_count = 0
                    last_restart_count_reset = current_time

                # Ensure the service is active
                if not self.is_service_running():
                    log.warning('Service not running — attempting to start...')
                    try:
                        subprocess.run(
                            ['sudo', 'systemctl', 'daemon-reload'],
                            capture_output=True, timeout=10,
                        )
                        subprocess.run(
                            ['sudo', 'systemctl', 'start', self.service_name],
                            capture_output=True, check=True, timeout=30,
                        )
                        log.info('Service started successfully.')
                        time.sleep(15)
                    except Exception as e:
                        log.error('Failed to start service: %s', e)
                        time.sleep(30)
                    continue

                healthy, status = self.check_process_health()

                if not healthy:
                    if 'Process not found' in status and self.is_service_running():
                        log.warning('Service running but process not accessible.')
                    elif self.should_restart_service(status):
                        if self.restart_service(status):
                            time.sleep(30)
                        else:
                            log.warning('Restart conditions not met — continuing monitoring.')
                    continue

                # Periodic network check (every 5 loops ≈ every 5 minutes)
                if loop_count % 5 == 0:
                    network_ok = self.check_network_connectivity()
                    if not network_ok and not network_down_logged:
                        log.warning('Network connectivity lost.')
                        network_down_logged = True
                    elif network_ok and network_down_logged:
                        log.info('Network connectivity restored.')
                        network_down_logged = False

                if not startup_complete and healthy:
                    log.info('Watchdog monitoring active — all systems nominal.')
                    startup_complete = True

                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                log.warning('Watchdog stopped by user.')
                break
            except Exception as e:
                log.error('Watchdog loop error: %s', e)
                time.sleep(self.check_interval)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == '__main__':
    log.info('=== WATCHDOG PROCESS STARTING ===')
    watchdog = MuseumWatchdog()

    if len(sys.argv) > 1 and sys.argv[1] == '--test-restart':
        log.warning('Running test mode: restarting service.')
        watchdog.restart_service('Test restart')

    elif len(sys.argv) > 1 and sys.argv[1] == '--status':
        service_running = watchdog.is_service_running()
        proc = watchdog.get_service_process()
        scene_running = watchdog._is_scene_running()
        print(f'Service active:  {service_running}')
        print(f'Process found:   {proc is not None}')
        print(f'Scene running:   {scene_running}')
        if proc:
            try:
                memory_mb = proc.memory_info().rss / 1024 / 1024
                cpu_percent = proc.cpu_percent(interval=1)
                print(f'Memory:          {memory_mb:.1f} MB')
                print(f'CPU:             {cpu_percent:.1f} %')
            except Exception:
                print('Could not get process stats.')

    else:
        watchdog.run()