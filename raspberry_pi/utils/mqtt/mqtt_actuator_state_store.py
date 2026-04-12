#!/usr/bin/env python3
"""
MQTT Actuator State Store - Runtime ON/OFF/UNKNOWN tracking for actuator endpoints.

Maintains per-endpoint desired and confirmed states derived from outgoing
commands and incoming feedback messages. Decouples UI state from scene
timeline simulation by providing a real hardware truth source.
"""

import time
import threading
from typing import Callable, Dict, Optional

from utils.logging_setup import get_logger


# Commands that imply an ON state
_ON_PREFIXES = frozenset({'ON', '1', 'TRUE', 'START', 'ACTIVE'})
# Commands that imply an OFF state
_OFF_PREFIXES = frozenset({'OFF', '0', 'FALSE', 'STOP', 'INACTIVE'})


def _infer_state_from_command(command: str) -> Optional[str]:
    """
    Infer ON or OFF from a command string.

    Handles both plain commands ('ON', 'OFF') and colon-separated payloads
    ('ON:100:L', 'ON:50:R:5000') by splitting on ':' and checking the prefix.

    Args:
        command: Raw command string as sent to the device.

    Returns:
        'ON', 'OFF', or None if the command cannot be mapped.
    """
    if not command:
        return None
    prefix = str(command).strip().upper().split(':')[0]
    if prefix in _ON_PREFIXES:
        return 'ON'
    if prefix in _OFF_PREFIXES:
        return 'OFF'
    return None


class ActuatorState:
    """Immutable-by-convention record for a single endpoint's runtime state."""

    __slots__ = (
        'topic', 'desired_state', 'confirmed_state',
        'state_source', 'last_update_ts', 'node_id', 'stale',
    )

    def __init__(self, topic: str) -> None:
        self.topic: str = topic
        self.desired_state: Optional[str] = None
        self.confirmed_state: str = 'UNKNOWN'
        self.state_source: str = 'none'
        self.last_update_ts: float = time.time()
        self.node_id: Optional[str] = None
        self.stale: bool = False

    def to_dict(self) -> dict:
        return {
            'topic': self.topic,
            'desired_state': self.desired_state,
            'confirmed_state': self.confirmed_state,
            'state_source': self.state_source,
            'last_update_ts': self.last_update_ts,
            'node_id': self.node_id,
            'stale': self.stale,
        }


class MQTTActuatorStateStore:
    """
    Thread-safe runtime state store for MQTT actuator endpoints.

    Tracks desired state (from outgoing commands) and confirmed state
    (from feedback messages) independently. Fires an optional callback
    on every state change for real-time WebSocket propagation.

    Intended usage:
    - Call update_desired() immediately after mqtt_client.publish().
    - Call update_confirmed() when feedback OK/ERROR arrives.
    - Call mark_node_offline() when a device node disconnects.
    - Call get_all_states() to serve the /api/device_states endpoint.
    """

    def __init__(self, logger=None) -> None:
        self.logger = logger or get_logger('actuator_store')
        self._states: Dict[str, ActuatorState] = {}
        self._lock = threading.Lock()
        self._update_callback: Optional[Callable[[dict], None]] = None

    # ==========================================================================
    # CONFIGURATION
    # ==========================================================================

    def set_update_callback(self, callback: Callable[[dict], None]) -> None:
        """
        Register a callback invoked on every state change.

        The callback receives a single snapshot dict (from ActuatorState.to_dict())
        and must be non-blocking. Typically used to emit WebSocket events.

        Args:
            callback: Callable accepting a state snapshot dict.
        """
        self._update_callback = callback

    # ==========================================================================
    # STATE UPDATES
    # ==========================================================================

    def update_desired(
        self,
        topic: str,
        command: str,
        node_id: Optional[str] = None,
    ) -> None:
        """
        Record the desired state for an endpoint based on a published command.

        Skips update if the command cannot be mapped to ON/OFF (e.g. SPEED,
        DIR, or custom payloads that do not change the binary on/off state).

        Args:
            topic: MQTT topic the command was published to.
            command: Raw command payload string.
            node_id: Identifier of the node that owns this endpoint (optional).
        """
        inferred = _infer_state_from_command(command)
        if inferred is None:
            return

        with self._lock:
            entry = self._get_or_create(topic)
            entry.desired_state = inferred
            entry.last_update_ts = time.time()
            entry.stale = False
            if node_id:
                entry.node_id = node_id
            snapshot = entry.to_dict()

        self.logger.debug(f"Desired: {topic} -> {inferred}")
        self._notify(snapshot)

    def update_confirmed(
        self,
        topic: str,
        command: str,
        source: str = 'feedback',
    ) -> None:
        """
        Record the confirmed state for an endpoint after a successful feedback.

        If the command cannot be mapped (e.g. unknown payload), only the
        source and timestamp are updated while confirmed_state remains unchanged.

        Args:
            topic: MQTT topic the original command was sent to.
            command: Raw command payload that produced the feedback.
            source: Origin of the confirmation ('feedback', 'state', 'manual').
        """
        inferred = _infer_state_from_command(command)

        with self._lock:
            entry = self._get_or_create(topic)
            if inferred is not None:
                entry.confirmed_state = inferred
            entry.state_source = source
            entry.last_update_ts = time.time()
            entry.stale = False
            snapshot = entry.to_dict()

        self.logger.debug(
            f"Confirmed: {topic} -> {entry.confirmed_state} ({source})"
        )
        self._notify(snapshot)

    def mark_node_offline(
        self,
        node_id: str,
        policy: str = 'UNKNOWN',
    ) -> None:
        """
        Mark all endpoints owned by a node as stale when the node disconnects.

        The confirmed_state is set to the given policy value ('UNKNOWN' is the
        safe default; 'OFF' may be appropriate for safety-critical systems).
        Only endpoints that are not already stale are updated.

        Args:
            node_id: Identifier of the disconnected node.
            policy: State to assign to affected endpoints ('UNKNOWN' or 'OFF').
        """
        affected = []
        with self._lock:
            for entry in self._states.values():
                if entry.node_id == node_id and not entry.stale:
                    entry.confirmed_state = policy
                    entry.stale = True
                    entry.last_update_ts = time.time()
                    affected.append(entry.to_dict())

        for snapshot in affected:
            self.logger.warning(
                f"Node '{node_id}' offline -> {snapshot['topic']} = {policy}"
            )
            self._notify(snapshot)

    # ==========================================================================
    # QUERIES
    # ==========================================================================

    def get_all_states(self) -> list:
        """
        Return a snapshot of all tracked endpoint states.

        Returns:
            List of state dicts, one per tracked endpoint.
        """
        with self._lock:
            return [entry.to_dict() for entry in self._states.values()]

    def get_state(self, topic: str) -> Optional[dict]:
        """
        Return the state snapshot for a single endpoint.

        Args:
            topic: MQTT topic to look up.

        Returns:
            State dict or None if the topic has not been tracked yet.
        """
        with self._lock:
            entry = self._states.get(topic)
            return entry.to_dict() if entry else None

    # ==========================================================================
    # INTERNAL HELPERS
    # ==========================================================================

    def _get_or_create(self, topic: str) -> ActuatorState:
        if topic not in self._states:
            self._states[topic] = ActuatorState(topic)
        return self._states[topic]

    def _notify(self, snapshot: dict) -> None:
        if self._update_callback:
            try:
                self._update_callback(snapshot)
            except Exception as exc:
                self.logger.error(f"State update callback error: {exc}")