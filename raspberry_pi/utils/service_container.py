#!/usr/bin/env python3
"""
Service Container - Centralized management of system services and components.
"""

import sys
from utils.logging_setup import get_logger

# Component imports
try:
    from utils.mqtt.mqtt_client import MQTTClient
    from utils.mqtt.mqtt_message_handler import MQTTMessageHandler
    from utils.mqtt.mqtt_feedback_tracker import MQTTFeedbackTracker
    from utils.mqtt.mqtt_device_registry import MQTTDeviceRegistry
    from utils.audio_handler import AudioHandler
    from utils.video_handler import VideoHandler
    from utils.system_monitor import SystemMonitor
    from utils.button_handler import ButtonHandler
except ImportError as e:
    # Logger may not be available yet at this point — use print
    print(f"CRITICAL: Failed to import core modules in ServiceContainer: {e}")
    sys.exit(1)


class ServiceContainer:
    """
    Centralized service container for initializing and managing all system components.

    Handles ordered initialization, dependency wiring, and graceful cleanup
    of audio, video, MQTT, system monitor, and button handler components.
    """

    def __init__(self, config, room_id, logger=None):
        """
        Initialize the service container with configuration and room context.

        Args:
            config: Flat configuration dictionary as returned by ConfigManager.
            room_id: Unique identifier for the current room.
            logger: Logger instance for service lifecycle events.
        """
        self.config = config
        self.room_id = room_id
        self.log = logger or get_logger('ServiceContainer')

        # Components — populated by init_all_services()
        self.audio_handler = None
        self.video_handler = None
        self.mqtt_client = None
        self.mqtt_message_handler = None
        self.mqtt_feedback_tracker = None
        self.mqtt_device_registry = None
        self.system_monitor = None
        self.button_handler = None

    def init_all_services(self):
        """
        Initialize all services in dependency order.

        Returns:
            ServiceContainer: Returns self to allow method chaining.
        """
        self.log.info("Initializing system services...")

        self._init_audio()
        self._init_video()
        self._init_mqtt()
        self._init_system_monitor()
        self._init_button_handler()

        self.log.info("All services initialized.")
        return self

    def _init_audio(self):
        """Initialize the audio handler. Sets to None on failure."""
        try:
            self.audio_handler = AudioHandler(
                self.config['audio_dir'],
                max_init_attempts=self.config.get('audio_max_init_attempts', 3),
                init_retry_delay=self.config.get('audio_init_retry_delay', 5)
            )
        except Exception as e:
            self.log.warning(f"Audio handler initialization failed: {e}")
            self.audio_handler = None

    def _init_video(self):
        """Initialize the video handler. Sets to None on failure."""
        try:
            self.video_handler = VideoHandler(
                video_dir=self.config['video_dir'],
                ipc_socket=self.config['ipc_socket'],
                iddle_image=self.config['iddle_image'],
                health_check_interval=self.config['video_health_check_interval'],
                max_restart_attempts=self.config['video_max_restart_attempts'],
                restart_cooldown=self.config['video_restart_cooldown']
            )
        except Exception as e:
            self.log.warning(f"Video handler initialization failed: {e}")
            self.video_handler = None

    def _init_mqtt(self):
        """
        Initialize all MQTT components and wire them together.

        Initialization order:
        1. Device registry
        2. Feedback tracker
        3. Message handler (scene callbacks are set later in the controller)
        4. MQTT client (connected to the above handlers)
        """
        # 1. Device Registry
        self.mqtt_device_registry = MQTTDeviceRegistry(
            device_timeout=int(self.config.get('device_timeout', 180))
        )

        # 2. Feedback Tracker
        self.mqtt_feedback_tracker = MQTTFeedbackTracker(
            feedback_timeout=float(self.config.get('feedback_timeout', 2))
        )

        # 3. Message Handler (scene callbacks are set in the controller)
        self.mqtt_message_handler = MQTTMessageHandler(room_id=self.room_id)

        # 4. MQTT Client
        self.mqtt_client = MQTTClient(
            broker_host=self.config['broker_ip'],
            broker_port=int(self.config['port']),
            client_id=f"{self.room_id}_controller",
            room_id=self.room_id,
            retry_attempts=self.config.get('mqtt_retry_attempts', 3),
            retry_sleep=self.config.get('mqtt_retry_sleep', 2),
            connect_timeout=self.config.get('mqtt_connect_timeout', 10),
            reconnect_timeout=self.config.get('mqtt_reconnect_timeout', 5),
            reconnect_sleep=self.config.get('mqtt_reconnect_sleep', 0.5),
            check_interval=self.config.get('mqtt_check_interval', 60)
        )

        # Wire the client to its internal handlers
        self.mqtt_client.set_handlers(
            self.mqtt_message_handler,
            self.mqtt_feedback_tracker,
            self.mqtt_device_registry
        )

    def _init_system_monitor(self):
        """Initialize the system monitor and log startup information."""
        self.system_monitor = SystemMonitor(
            health_check_interval=self.config.get('health_check_interval', 120)
        )
        self.system_monitor.log_startup_info(
            self.room_id,
            self.config['broker_ip'],
            self.config['button_pin']
        )

    def _init_button_handler(self):
        """
        Initialize the physical button handler. Sets to None on failure.

        Note: The button callback is assigned later in the controller.
        """
        try:
            self.button_handler = ButtonHandler(
                pin=self.config['button_pin'],
                debounce_time=self.config.get('debounce_time', 300)
            )
            # Callback is set in the controller
        except Exception as e:
            self.log.warning(f"Button handler initialization failed: {e}")
            self.button_handler = None

    def cleanup(self):
        """
        Safely shut down all active services.

        Cleans up the MQTT client first, then attempts cleanup on all
        remaining components, logging any errors without raising exceptions.
        """
        self.log.info("Cleaning up services...")

        if self.mqtt_client:
            self.mqtt_client.cleanup()

        components = [
            (self.button_handler, "Button Handler"),
            (self.audio_handler, "Audio Handler"),
            (self.video_handler, "Video Handler")
        ]

        for component, name in components:
            if component and hasattr(component, 'cleanup'):
                try:
                    component.cleanup()
                except Exception as e:
                    self.log.error(f"{name} cleanup error: {e}")