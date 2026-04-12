import { useState, useEffect, useCallback } from 'react';
import { socket } from '../services/socket';
import { api } from '../services/api';

/**
 * Subscribes to real-time actuator endpoint states from the backend.
 *
 * On mount:
 *  1. Fetches the full state snapshot from GET /api/device_states.
 *  2. Subscribes to incremental `device_runtime_state_update` socket events.
 *  3. Re-fetches on socket reconnect to recover any missed updates.
 *
 * Keyed by MQTT topic so lookups are O(1) regardless of device count.
 *
 * @returns {{ deviceStates: Object, getStateForDevice: Function, isLoading: boolean }}
 */
export function useDeviceRuntimeState() {
    const [deviceStates, setDeviceStates] = useState({});
    const [isLoading, setIsLoading] = useState(true);

    const fetchAll = useCallback(async () => {
        try {
            const states = await api.getDeviceStates();
            const byTopic = {};
            states.forEach((s) => {
                byTopic[s.topic] = s;
            });
            setDeviceStates(byTopic);
        } catch {
            // Backend may not have the store yet — degrade gracefully
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAll();

        const handleUpdate = (snapshot) => {
            setDeviceStates((prev) => ({
                ...prev,
                [snapshot.topic]: snapshot,
            }));
        };

        // Re-fetch full snapshot on reconnect to recover missed incremental events
        const handleReconnect = () => fetchAll();

        socket.on('device_runtime_state_update', handleUpdate);
        socket.on('connect', handleReconnect);

        return () => {
            socket.off('device_runtime_state_update', handleUpdate);
            socket.off('connect', handleReconnect);
        };
    }, [fetchAll]);

    /**
     * Resolve the display state for a device object from devices.json.
     *
     * @param {Object} device - Device object with at least a `topic` field.
     * @returns {'ON' | 'OFF' | 'UNKNOWN'} Confirmed hardware state.
     */
    const getStateForDevice = useCallback(
        (device) => {
            if (!device?.topic) return 'UNKNOWN';
            const entry = deviceStates[device.topic];
            if (!entry || entry.stale) return 'UNKNOWN';
            return entry.confirmed_state ?? 'UNKNOWN';
        },
        [deviceStates],
    );

    /**
     * Format human-readable runtime state per device kind.
     * Motors show direction + speed when available, relays stay ON/OFF.
     */
    const getDisplayStateForDevice = useCallback(
        (device) => {
            if (!device?.topic) return 'UNKNOWN';
            const entry = deviceStates[device.topic];
            if (!entry || entry.stale) return 'UNKNOWN';

            const confirmed = entry.confirmed_state ?? 'UNKNOWN';
            if (device.type !== 'motor') {
                return confirmed;
            }

            if (confirmed !== 'ON') {
                return confirmed;
            }

            const direction = entry.motor_direction ?? '?';
            const speed = Number.isFinite(entry.motor_speed)
                ? `${entry.motor_speed}%`
                : '?%';
            return `${direction} ${speed}`;
        },
        [deviceStates],
    );

    return { deviceStates, getStateForDevice, getDisplayStateForDevice, isLoading };
}