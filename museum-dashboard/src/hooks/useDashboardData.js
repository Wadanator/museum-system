import { useState, useEffect } from 'react';
import { socket } from '../services/socket';

export function useDashboardData() {
  const [status, setStatus] = useState({
    room_id: '-',
    scene_running: false,
    mqtt_connected: false
  });
  
  const [deviceCount, setDeviceCount] = useState(0);
  
  const [progressData, setProgressData] = useState({
    progress: 0,
    text: '0%',
    info: 'Načítavam...',
    visible: false
  });

  useEffect(() => {
    // Handlere
    const handleStatus = (data) => setStatus(data);
    
    const handleStats = (data) => {
      if (data.connected_devices) {
        setDeviceCount(Object.keys(data.connected_devices).length);
      }
    };

    const handleSceneProgress = (data) => {
        if (data.scene_running && data.mode === 'state_machine') {
            const percent = Math.min(Math.max(data.progress * 100, 0), 100);
            const stateInfo = `Stav: ${data.current_state} (${data.states_completed}/${data.total_states})`;
            
            setProgressData({
                progress: percent,
                text: `${Math.round(percent)}%`,
                info: stateInfo,
                visible: true
            });
        } else {
            setProgressData(prev => ({ ...prev, visible: false }));
        }
    };

    // Listeners
    socket.on('status_update', handleStatus);
    socket.on('stats_update', handleStats);
    socket.on('scene_progress_update', handleSceneProgress);

    // Initial fetch
    socket.emit('request_status');
    socket.emit('request_stats');

    // Cleanup
    return () => {
      socket.off('status_update', handleStatus);
      socket.off('stats_update', handleStats);
      socket.off('scene_progress_update', handleSceneProgress);
    };
  }, []);

  // Reset progress when scene stops
  useEffect(() => {
    if (!status.scene_running) {
        setProgressData(prev => ({ ...prev, visible: false }));
    }
  }, [status.scene_running]);

  return { status, deviceCount, progressData };
}