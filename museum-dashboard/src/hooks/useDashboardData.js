import { useState, useEffect } from 'react';
import { socket } from '../services/socket';

export function useDashboardData() {
  const [status, setStatus] = useState({
    room_id: '-',
    scene_running: false,
    mqtt_connected: false
  });

  const [deviceCount, setDeviceCount] = useState(0);

  useEffect(() => {
    const handleStatus = (data) => setStatus(data);

    const handleStats = (data) => {
      if (data.connected_devices) {
        setDeviceCount(Object.keys(data.connected_devices).length);
      }
    };

    const handleConnect = () => {
      socket.emit('request_status');
      socket.emit('request_stats');
    };

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        socket.emit('request_status');
        socket.emit('request_stats');
      }
    };

    socket.on('status_update', handleStatus);
    socket.on('stats_update', handleStats);
    socket.on('connect', handleConnect);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Initial request on mount
    socket.emit('request_status');
    socket.emit('request_stats');

    return () => {
      socket.off('status_update', handleStatus);
      socket.off('stats_update', handleStats);
      socket.off('connect', handleConnect);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return { status, deviceCount };
};