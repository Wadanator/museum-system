#!/usr/bin/env python3
"""
MQTT Actuator State Store - Runtime ON/OFF/UNKNOWN tracking for actuator endpoints.

Maintains per-endpoint desired and confirmed states derived from outgoing
commands and incoming feedback messages. Decouples UI state from scene
timeline simulation by providing a real hardware truth source.
"""

import json
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


def _normalize_direction(direction: str) -> Optional[str]:
    """Normalize motor direction aliases to stable values (LEFT/RIGHT)."""
    if not direction:
        return None
    raw = str(direction).strip().upper()
    if raw in {'L', 'LEFT', 'CCW', 'REV', 'REVERSE', 'BWD', 'BACKWARD'}:
        return 'LEFT'
    if raw in {'R', 'RIGHT', 'CW', 'FWD', 'FORWARD'}:
        return 'RIGHT'
    return None


def _extract_motor_fields(command: str) -> dict:
    """
    Parse motor-specific metadata from command payload.

    Expected patterns include:
    - ON:<speed>:<direction>
    - ON:<speed>:<direction>:<duration_ms>
    - OFF
    """
    if not command:
        return {'motor_direction': None, 'motor_speed': None}

    parts = str(command).strip().split(':')
    prefix = parts[0].upper() if parts else ''

    if prefix in _OFF_PREFIXES:
        return {'motor_direction': None, 'motor_speed': 0}

    if prefix == 'SPEED':
        speed = None
        if len(parts) > 1:
            try:
                speed = int(parts[1])
            except (ValueError, TypeError):
                speed = None
        return {'motor_direction': None, 'motor_speed': speed}

    if prefix in {'DIR', 'DIRECTION'}:
        direction = _normalize_direction(parts[1]) if len(parts) > 1 else None
        return {'motor_direction': direction, 'motor_speed': None}

    if prefix not in _ON_PREFIXES:
        return {'motor_direction': None, 'motor_speed': None}

    speed = None
    if len(parts) > 1:
        try:
            speed = int(parts[1])
        except (ValueError, TypeError):
            speed = None

    direction = _normalize_direction(parts[2]) if len(parts) > 2 else None
    return {'motor_direction': direction, 'motor_speed': speed}


def _coerce_int(value) -> Optional[int]:
    """Best-effort integer conversion for JSON state payload metadata."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_state_payload(payload: str) -> dict:
    """
    Parse a retained /state payload.

    Supports both the MVP plain payloads (ON/OFF/ACTIVE/INACTIVE) and compact
    JSON payloads such as {"state": "ON", "node_id": "..."}.
    """
    raw = '' if payload is None else str(payload).strip()
    if not raw:
        return {
            'state_command': '',
            'node_id': None,
            'source': 'state',
            'motor_direction': None,
            'motor_speed': None,
        }

    if raw.startswith('{'):
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return {
                'state_command': raw,
                'node_id': None,
                'source': 'state_invalid_json',
                'motor_direction': None,
                'motor_speed': None,
            }

        state = str(data.get('state', '')).strip()
        direction = _normalize_direction(data.get('direction'))
        speed = _coerce_int(data.get('speed'))
        return {
            'state_command': state,
            'node_id': data.get('node_id'),
            'source': str(data.get('source') or 'state'),
            'motor_direction': direction,
            'motor_speed': speed,
        }

    return {
        'state_command': raw,
        'node_id': None,
        'source': 'state',
        'motor_direction': None,
        'motor_speed': None,
    }


class ActuatorState:
    """Immutable-by-convention record for a single endpoint's runtime state."""

    __slots__ = (
        'topic', 'desired_state', 'confirmed_state',
        'reported_state', 'state_source', 'last_update_ts',
        'last_state_ts', 'node_id', 'stale', 'state_retained',
        'motor_direction', 'motor_speed',
    )

    def __init__(self, topic: str) -> None:
        self.topic: str = topic
        self.desired_state: Optional[str] = None
        self.confirmed_state: str = 'UNKNOWN'
        self.reported_state: Optional[str] = None
        self.state_source: str = 'none'
        self.last_update_ts: float = time.time()
        self.last_state_ts: Optional[float] = None
        self.node_id: Optional[str] = None
        self.stale: bool = False
        self.state_retained: bool = False
        self.motor_direction: Optional[str] = None
        self.motor_speed: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            'topic': self.topic,
            'desired_state': self.desired_state,
            'confirmed_state': self.confirmed_state,
            'reported_state': self.reported_state,
            'state_source': self.state_source,
            'last_update_ts': self.last_update_ts,
            'last_state_ts': self.last_state_ts,
            'node_id': self.node_id,
            'stale': self.stale,
            'state_retained': self.state_retained,
            'motor_direction': self.motor_direction,
            'motor_speed': self.motor_speed,
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

    def initialize_from_devices_config(self, devices_config: dict) -> int:
        """
        Create state entries for every configured actuator endpoint.

        Configured devices start stale/unknown so retained /state replay cannot
        accidentally look fresh before node availability is known.

        Args:
            devices_config: Parsed config/rooms/<room_id>/devices.json content.

        Returns:
            Number of configured MQTT topics registered in the store.
        """
        if not isinstance(devices_config, dict):
            self.logger.warning("Devices config is not an object; skipping state bootstrap")
            return 0

        configured = []
        for group_name in ('motors', 'relays', 'lights'):
            group = devices_config.get(group_name) or []
            if not isinstance(group, list):
                self.logger.warning("Devices config group '%s' is not a list", group_name)
                continue
            configured.extend(item for item in group if isinstance(item, dict))

        count = 0
        with self._lock:
            for item in configured:
                topic = str(item.get('topic') or '').strip()
                if not topic:
                    continue

                entry = self._get_or_create(topic)
                entry.node_id = item.get('node_id') or entry.node_id
                entry.confirmed_state = 'UNKNOWN'
                entry.state_source = 'config'
                entry.stale = True
                entry.last_update_ts = time.time()
                count += 1

                if not entry.node_id:
                    self.logger.warning(
                        "Configured actuator %s has no node_id; offline/stale "
                        "mapping will be incomplete",
                        topic,
                    )

        self.logger.info("Bootstrapped %d actuator state entries from devices config", count)
        return count

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
        motor_fields = _extract_motor_fields(command)
        has_motor_delta = (
            motor_fields['motor_direction'] is not None
            or motor_fields['motor_speed'] is not None
        )
        if inferred is None and not has_motor_delta:
            return

        with self._lock:
            entry = self._get_or_create(topic)
            if inferred is not None:
                entry.desired_state = inferred
            if motor_fields['motor_direction'] is not None:
                entry.motor_direction = motor_fields['motor_direction']
            if motor_fields['motor_speed'] is not None:
                entry.motor_speed = motor_fields['motor_speed']
            entry.last_update_ts = time.time()
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
        motor_fields = _extract_motor_fields(command)

        with self._lock:
            entry = self._get_or_create(topic)
            if inferred is not None:
                entry.confirmed_state = inferred
            if motor_fields['motor_direction'] is not None:
                entry.motor_direction = motor_fields['motor_direction']
            if motor_fields['motor_speed'] is not None:
                entry.motor_speed = motor_fields['motor_speed']
            entry.state_source = source
            entry.last_update_ts = time.time()
            snapshot = entry.to_dict()

        self.logger.debug(
            f"Confirmed: {topic} -> {entry.confirmed_state} ({source})"
        )
        self._notify(snapshot)

    def update_reported_state(
        self,
        topic: str,
        payload: str,
        node_id: Optional[str] = None,
        node_online: bool = False,
        retained: bool = False,
    ) -> None:
        """
        Record an authoritative /state report from an ESP32 node.

        A state report is stored even if the node is not considered online yet,
        but the Live view is marked fresh only when node_online is true.
        """
        parsed = _parse_state_payload(payload)
        inferred = _infer_state_from_command(parsed['state_command'])
        motor_fields = _extract_motor_fields(parsed['state_command'])
        if parsed['motor_direction'] is not None:
            motor_fields['motor_direction'] = parsed['motor_direction']
        if parsed['motor_speed'] is not None:
            motor_fields['motor_speed'] = parsed['motor_speed']

        if inferred is None and not any(
            value is not None for value in motor_fields.values()
        ):
            self.logger.warning(
                "Ignoring state report with unmapped payload: %s -> %s",
                topic,
                payload,
            )
            return

        payload_node_id = parsed.get('node_id')
        effective_node_id = node_id or payload_node_id
        now = time.time()

        with self._lock:
            entry = self._get_or_create(topic)
            if entry.node_id and payload_node_id and entry.node_id != payload_node_id:
                self.logger.warning(
                    "State payload node_id mismatch for %s: payload=%s config=%s; "
                    "using local mapping",
                    topic,
                    payload_node_id,
                    entry.node_id,
                )
            if not entry.node_id and effective_node_id:
                entry.node_id = effective_node_id

            if inferred is not None:
                entry.reported_state = inferred
                if node_online:
                    entry.confirmed_state = inferred
                    entry.stale = False
                else:
                    entry.confirmed_state = 'UNKNOWN'
                    entry.stale = True

            if motor_fields['motor_direction'] is not None:
                entry.motor_direction = motor_fields['motor_direction']
            if motor_fields['motor_speed'] is not None:
                entry.motor_speed = motor_fields['motor_speed']

            entry.state_source = parsed.get('source') or 'state'
            entry.last_state_ts = now
            entry.last_update_ts = now
            entry.state_retained = bool(retained)
            snapshot = entry.to_dict()

        self.logger.debug(
            "Reported state: %s -> %s (online=%s retained=%s)",
            topic,
            snapshot['reported_state'],
            node_online,
            retained,
        )
        self._notify(snapshot)

    def mark_node_online(self, node_id: str) -> None:
        """
        Mark endpoints fresh when their node is online and they have a state report.

        Online alone is not enough to clear stale. The endpoint must already have
        a reported_state from retained replay or a fresh /state message.
        """
        affected = []
        with self._lock:
            for entry in self._states.values():
                if entry.node_id != node_id or entry.reported_state is None:
                    continue
                if not entry.stale and entry.confirmed_state == entry.reported_state:
                    continue
                entry.confirmed_state = entry.reported_state
                entry.stale = False
                entry.last_update_ts = time.time()
                affected.append(entry.to_dict())

        for snapshot in affected:
            self.logger.info(
                "Node '%s' online + state report -> %s = %s",
                node_id,
                snapshot['topic'],
                snapshot['confirmed_state'],
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
                if entry.node_id == node_id and (
                    not entry.stale or entry.confirmed_state != policy
                ):
                    entry.confirmed_state = policy
                    entry.stale = True
                    entry.state_source = 'offline'
                    entry.last_update_ts = time.time()
                    affected.append(entry.to_dict())

        for snapshot in affected:
            self.logger.warning(
                f"Node '{node_id}' offline -> {snapshot['topic']} = {policy}"
            )
            self._notify(snapshot)

    def force_all_off(self, source: str = 'forced_stop') -> int:
        """
        Force all tracked endpoints into a deterministic OFF state.

        Useful for scene STOP operations where UI should immediately reflect
        safe OFF values even if feedback for last commands arrives late.

        Args:
            source: Marker stored in state_source for observability.

        Returns:
            Number of updated endpoint snapshots.
        """
        snapshots = []
        with self._lock:
            for entry in self._states.values():
                entry.desired_state = 'OFF'
                entry.state_source = source
                entry.last_update_ts = time.time()
                if entry.stale:
                    entry.confirmed_state = 'UNKNOWN'
                else:
                    entry.confirmed_state = 'OFF'
                    entry.reported_state = 'OFF'
                    entry.last_state_ts = entry.last_update_ts
                    entry.motor_direction = None
                    entry.motor_speed = 0
                snapshots.append(entry.to_dict())

        for snapshot in snapshots:
            self._notify(snapshot)

        if snapshots:
            self.logger.info(
                "Forced OFF applied to %d tracked endpoints (%s)",
                len(snapshots),
                source,
            )
        return len(snapshots)

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

    def get_node_id_for_topic(self, topic: str) -> Optional[str]:
        """Return the configured node_id for a command topic if known."""
        with self._lock:
            entry = self._states.get(topic)
            return entry.node_id if entry else None

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
