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
    // Handlere
    const handleStatus = (data) => setStatus(data);
    
    const handleStats = (data) => {
      if (data.connected_devices) {
        setDeviceCount(Object.keys(data.connected_devices).length);
      }
    };

    // Listeners
    socket.on('status_update', handleStatus);
    socket.on('stats_update', handleStats);

    // Initial fetch
    socket.emit('request_status');
    socket.emit('request_stats');

    // Cleanup
    return () => {
      socket.off('status_update', handleStatus);
      socket.off('stats_update', handleStats);
    };
  }, []);

  return { status, deviceCount };
}