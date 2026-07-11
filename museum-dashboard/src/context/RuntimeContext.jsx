import { useCallback, useEffect, useMemo, useState } from 'react';
import { socket } from '../services/socket';
import { api } from '../services/api';
import { RuntimeContext } from './RuntimeContextValue';

const DEFAULT_STATUS = {
  room_id: '-',
  scene_running: false,
  current_scene_name: null,
  active_state: null,
  mqtt_connected: false,
  uptime: 0,
  log_count: 0,
};

const mapStatesByTopic = (states = []) => {
  const byTopic = {};
  states.forEach((state) => {
    if (state?.topic) {
      byTopic[state.topic] = state;
    }
  });
  return byTopic;
};

const normalizeStatus = (status = {}) => {
  const next = {
    ...DEFAULT_STATUS,
    ...status,
  };

  if (!next.scene_running) {
    next.active_state = null;
    next.current_scene_name = null;
  }

  return next;
};

export function RuntimeProvider({ children }) {
  const [status, setStatus] = useState(DEFAULT_STATUS);
  const [deviceStates, setDeviceStates] = useState({});
  const [connectedDevices, setConnectedDevices] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [lastRuntimeSync, setLastRuntimeSync] = useState(null);

  const applyRuntimeSnapshot = useCallback((snapshot) => {
    if (!snapshot) return;

    if (snapshot.status) {
      setStatus((prev) => normalizeStatus({ ...prev, ...snapshot.status }));
    }

    if (Array.isArray(snapshot.device_states)) {
      setDeviceStates(mapStatesByTopic(snapshot.device_states));
    }

    if (snapshot.connected_devices) {
      setConnectedDevices(snapshot.connected_devices);
    }

    setLastRuntimeSync(Date.now());
    setIsLoading(false);
  }, []);

  const refreshRuntime = useCallback(async () => {
    try {
      const snapshot = await api.getRuntime();
      applyRuntimeSnapshot(snapshot);
    } catch {
      // Socket events can still keep the UI alive when REST refresh fails.
      setIsLoading(false);
    }
  }, [applyRuntimeSnapshot]);

  useEffect(() => {
    const initialRefreshTimer = window.setTimeout(() => {
      refreshRuntime();
    }, 0);

    const handleRuntimeSnapshot = (snapshot) => {
      applyRuntimeSnapshot(snapshot);
    };

    const handleStatus = (nextStatus) => {
      setStatus((prev) => normalizeStatus({ ...prev, ...nextStatus }));
    };

    const handleProgress = (data) => {
      if (!data?.activeState) return;
      setStatus((prev) => normalizeStatus({
        ...prev,
        scene_running: true,
        active_state: data.activeState,
        current_scene_name: data.sceneName ?? prev.current_scene_name,
      }));
    };

    const handleDeviceUpdate = (snapshot) => {
      if (!snapshot?.topic) return;
      setDeviceStates((prev) => ({
        ...prev,
        [snapshot.topic]: snapshot,
      }));
      setLastRuntimeSync(Date.now());
    };

    const handleConnect = () => {
      socket.emit('request_runtime');
      refreshRuntime();
    };

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        socket.emit('request_runtime');
        refreshRuntime();
      }
    };

    socket.on('runtime_snapshot', handleRuntimeSnapshot);
    socket.on('status_update', handleStatus);
    socket.on('scene_progress', handleProgress);
    socket.on('device_runtime_state_update', handleDeviceUpdate);
    socket.on('connect', handleConnect);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    socket.emit('request_runtime');

    return () => {
      window.clearTimeout(initialRefreshTimer);
      socket.off('runtime_snapshot', handleRuntimeSnapshot);
      socket.off('status_update', handleStatus);
      socket.off('scene_progress', handleProgress);
      socket.off('device_runtime_state_update', handleDeviceUpdate);
      socket.off('connect', handleConnect);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [applyRuntimeSnapshot, refreshRuntime]);

  const getEntryForDevice = useCallback(
    (device) => {
      if (!device?.topic) return null;
      return deviceStates[device.topic] ?? null;
    },
    [deviceStates],
  );

  const getStateForDevice = useCallback(
    (device) => {
      const entry = getEntryForDevice(device);
      if (!entry || entry.stale) return 'UNKNOWN';
      return entry.confirmed_state ?? 'UNKNOWN';
    },
    [getEntryForDevice],
  );

  const getDisplayStateForDevice = useCallback(
    (device) => {
      const entry = getEntryForDevice(device);
      if (!entry || entry.stale) return 'UNKNOWN';

      const confirmed = entry.confirmed_state ?? 'UNKNOWN';
      if (device.type === 'window') {
        if (!['OPENING', 'CLOSING'].includes(confirmed)) {
          return confirmed;
        }
        const speed = Number.isFinite(entry.motor_speed)
          ? `${entry.motor_speed}%`
          : '?%';
        return `${confirmed} ${speed}`;
      }

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
    [getEntryForDevice],
  );

  const resetActiveState = useCallback(() => {
    setStatus((prev) => normalizeStatus({ ...prev, active_state: null }));
  }, []);

  const runtimeSummary = useMemo(() => {
    const entries = Object.values(deviceStates);
    return entries.reduce(
      (acc, entry) => {
        acc.total += 1;
        if (entry.stale) {
          acc.stale += 1;
          acc.unknown += 1;
          return acc;
        }

        const confirmed = entry.confirmed_state ?? 'UNKNOWN';
        if (['ON', 'OPEN', 'OPENING', 'CLOSING'].includes(confirmed)) acc.on += 1;
        else if (['OFF', 'CLOSED', 'STOPPED'].includes(confirmed)) acc.off += 1;
        else acc.unknown += 1;

        if (
          entry.desired_state
          && entry.desired_state !== confirmed
          && !entry.stale
        ) {
          acc.pending += 1;
        }

        return acc;
      },
      { total: 0, on: 0, off: 0, unknown: 0, stale: 0, pending: 0 },
    );
  }, [deviceStates]);

  const value = useMemo(() => ({
    status,
    activeState: status.active_state ?? null,
    currentSceneName: status.current_scene_name ?? null,
    sceneRunning: Boolean(status.scene_running),
    deviceStates,
    connectedDevices,
    runtimeSummary,
    isLoading,
    lastRuntimeSync,
    refreshRuntime,
    getEntryForDevice,
    getStateForDevice,
    getDisplayStateForDevice,
    resetActiveState,
  }), [
    status,
    deviceStates,
    connectedDevices,
    runtimeSummary,
    isLoading,
    lastRuntimeSync,
    refreshRuntime,
    getEntryForDevice,
    getStateForDevice,
    getDisplayStateForDevice,
    resetActiveState,
  ]);

  return (
    <RuntimeContext.Provider value={value}>
      {children}
    </RuntimeContext.Provider>
  );
}


