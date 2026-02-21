#!/usr/bin/env python3
"""
MQTT Client with robust connection management and retry logic.

Handles MQTT broker connections, message publishing/subscribing, and integrates
with external handlers for message processing, feedback tracking, and device registry.
"""

import paho.mqtt.client as mqtt
import json
import time
from utils.logging_setup import get_logger
from utils.mqtt.topic_rules import MQTTRoomTopics


class MQTTClient:
    """
    MQTT Client with connection management and handler integration.

    Provides robust MQTT connectivity with automatic reconnection,
    retry logic, and integration points for external handlers.
    """

    def __init__(self, broker_host, broker_port=1883, client_id=None, logger=None,
                 room_id=None, retry_attempts=3, retry_sleep=2, connect_timeout=10,
                 reconnect_timeout=5, reconnect_sleep=0.5, check_interval=60):
        """Initialize MQTT client with connection and retry parameters."""

        # === Basic Connection Settings ===
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.room_id = room_id
        self.connected = False
        self.logger = logger or get_logger('mqtt')

        # === Connection Parameters ===
        self.retry_attempts = retry_attempts
        self.retry_sleep = retry_sleep
        self.connect_timeout = connect_timeout
        self.reconnect_timeout = reconnect_timeout
        self.reconnect_sleep = reconnect_sleep
        self.check_interval = check_interval

        # === State Management ===
        self.shutdown_requested = False
        self.connection_lost_callback = None
        self.connection_restored_callback = None

        # === External Handlers (injected after initialization) ===
        self.message_handler = None
        self.feedback_tracker = None
        self.device_registry = None

        # === Initialize MQTT Client ===
        self._setup_mqtt_client(client_id)

    def _setup_mqtt_client(self, client_id):
        """Initialize MQTT client with version compatibility and callbacks."""
        # Fix for paho-mqtt 2.0+ compatibility
        try:
            self.client = mqtt.Client(
                client_id=client_id,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1
            )
        except TypeError:
            self.client = mqtt.Client(client_id=client_id)

        # Set up callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish

    # ==========================================================================
    # HANDLER INJECTION METHODS
    # ==========================================================================

    def set_handlers(self, message_handler=None, feedback_tracker=None,
                     device_registry=None):
        """
        Set external handlers for message processing.

        Args:
            message_handler: Handler object with a handle_message() method.
            feedback_tracker: Tracker object for published message feedback.
            device_registry: Registry object for device management.
        """
        self.message_handler = message_handler
        self.feedback_tracker = feedback_tracker
        self.device_registry = device_registry

    def set_connection_callbacks(self, lost_callback=None, restored_callback=None):
        """
        Set callbacks for connection state changes.

        Args:
            lost_callback: Callable invoked when connection is lost.
            restored_callback: Callable invoked when connection is restored.
        """
        self.connection_lost_callback = lost_callback
        self.connection_restored_callback = restored_callback

    # ==========================================================================
    # MQTT CALLBACK HANDLERS
    # ==========================================================================

    def _on_connect(self, client, userdata, flags, rc):
        """
        Handle connection success or failure from the broker.

        Args:
            client: The MQTT client instance.
            userdata: User-defined data passed to the callback.
            flags: Response flags from the broker.
            rc: Connection result code (0 indicates success).
        """
        if rc == 0:
            was_connected = self.connected
            self.connected = True
            self.logger.info(
                f"MQTT connected to {self.broker_host}:{self.broker_port}"
            )

            # Subscribe to all room-specific topics
            room_topics = MQTTRoomTopics(self.room_id)
            for topic in room_topics.subscriptions():
                self.subscribe(topic)

            # Notify connection restored callback if this is a reconnection
            if not was_connected and self.connection_restored_callback:
                self.connection_restored_callback()
        else:
            self.connected = False
            self.logger.error(
                f"Failed to connect to MQTT broker. Return code: {rc}"
            )

    def _on_disconnect(self, client, userdata, rc):
        """
        Handle disconnection from the broker.

        Args:
            client: The MQTT client instance.
            userdata: User-defined data passed to the callback.
            rc: Disconnection result code.
        """
        was_connected = self.connected
        self.connected = False

        # Only log disconnection if we were actually connected before
        if was_connected:
            self.logger.warning(
                f"Disconnected from MQTT broker. Return code: {rc}"
            )
            if self.connection_lost_callback:
                self.connection_lost_callback()

    def _on_message(self, client, userdata, msg):
        """
        Delegate incoming message handling to the external message handler.

        Args:
            client: The MQTT client instance.
            userdata: User-defined data passed to the callback.
            msg: The received MQTT message object.
        """
        if self.message_handler:
            self.message_handler.handle_message(msg)

    def _on_publish(self, client, userdata, mid):
        """
        Handle acknowledgement of a successfully published message.

        Args:
            client: The MQTT client instance.
            userdata: User-defined data passed to the callback.
            mid: Message ID of the published message.
        """
        self.logger.debug(f"Message published with ID: {mid}")

    # ==========================================================================
    # MESSAGE PUBLISHING
    # ==========================================================================

    def publish(self, topic, message, qos=0, retain=False):
        """
        Publish a message to an MQTT topic.

        Args:
            topic: MQTT topic to publish to.
            message: Message payload to send.
            qos: Quality of Service level (0, 1, or 2).
            retain: Whether to retain the message on the broker.

        Returns:
            bool: True if the message was published successfully, False otherwise.
        """
        if not self.connected:
            self.logger.warning(
                f"Cannot publish to {topic}: Not connected to broker"
            )
            return False

        try:
            # Publish the message
            result = self.client.publish(topic, message, qos=qos, retain=retain)

            if result.rc == 0:
                self.logger.debug(f"Published to {topic}: {message}")

                # Track the message for feedback if feedback tracker is available
                if self.feedback_tracker:
                    self.feedback_tracker.track_published_message(topic, message)

                return True
            else:
                self.logger.error(
                    f"Failed to publish to {topic}. Return code: {result.rc}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Exception during publish to {topic}: {e}")
            return False

    # ==========================================================================
    # CONNECTION MANAGEMENT
    # ==========================================================================

    def connect(self, timeout=10):
        """
        Attempt a single connection to the MQTT broker.

        Args:
            timeout: Seconds to wait for connection to be established.

        Returns:
            bool: True if connected successfully, False otherwise.
        """
        try:
            # Clean up existing connection if present
            if hasattr(self.client, '_sock') and self.client._sock:
                self.client.disconnect()

            self.client.connect(self.broker_host, self.broker_port, timeout)
            self.client.loop_start()

            # Wait for connection confirmation with timeout
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            return self.connected

        except Exception as e:
            self.logger.error(f"Error connecting to MQTT broker: {e}")
            return False

    def connect_with_retry(self):
        """
        Connect to the MQTT broker with retry logic.

        Returns:
            bool: True if connection was established within the allowed attempts,
                  False otherwise.
        """
        for attempt in range(self.retry_attempts):
            if self.shutdown_requested:
                return False

            self.logger.info(
                f"MQTT connection attempt {attempt + 1}/{self.retry_attempts}"
            )

            if self.connect(self.connect_timeout):
                return True

            if attempt < self.retry_attempts - 1:
                time.sleep(self.retry_sleep)

        return False

    def establish_initial_connection(self):
        """
        Establish the initial MQTT connection with error handling.

        Returns:
            bool: True if the connection was established, False otherwise.
        """
        if not self.connect_with_retry():
            self.logger.critical("CRITICAL: Unable to establish MQTT connection")
            return False
        return True

    def check_and_reconnect(self):
        """
        Check the current connection and attempt reconnection if needed.

        Returns:
            bool: True if connected (or reconnected) successfully, False otherwise.
        """
        if not self.connected:
            self.logger.debug("MQTT connection lost, attempting to reconnect...")

            if self.connect_with_retry():
                self.logger.info("MQTT connection restored")
                return True
            else:
                return False
        return True

    def manage_connection_health(self):
        """
        Manage MQTT connection health and return current connection status.

        Returns:
            bool: True if the connection is healthy, False otherwise.
        """
        if not self.check_and_reconnect():
            return False
        elif self.is_connected():
            return True
        return False

    # ==========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ==========================================================================

    def subscribe(self, topic, qos=0):
        """
        Subscribe to an MQTT topic.

        Args:
            topic: The MQTT topic string to subscribe to.
            qos: Quality of Service level for the subscription (0, 1, or 2).

        Returns:
            bool: True if subscription was successful, False otherwise.
        """
        if not self.connected:
            self.logger.warning("Not connected to MQTT broker")
            return False

        try:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Subscribed to topic: {topic}")
                return True
            else:
                self.logger.error(
                    f"Failed to subscribe to {topic}: RC {result[0]}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Error subscribing to topic: {e}")
            return False

    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================

    def is_connected(self):
        """
        Check whether the client is currently connected to the broker.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self.connected

    def disconnect(self):
        """Disconnect from the MQTT broker and stop the network loop."""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.warning("MQTT disconnected")

    def cleanup(self):
        """Clean up MQTT client resources and signal shutdown."""
        self.shutdown_requested = True
        self.disconnect()
        self.logger.debug("MQTT client cleaned up")