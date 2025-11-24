import { useState, useEffect, useRef } from 'react';
import { socket } from '../../services/socket';
import { api } from '../../services/api';
import toast from 'react-hot-toast';
import { useConfirm } from '../../context/ConfirmContext';

export default function MainDashboard() {
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

  const progressInterval = useRef(null);
  const { confirm } = useConfirm();

  useEffect(() => {
    const handleStatus = (data) => setStatus(data);
    const handleStats = (data) => {
      if (data.connected_devices) {
        setDeviceCount(Object.keys(data.connected_devices).length);
      }
    };

    socket.on('status_update', handleStatus);
    socket.on('stats_update', handleStats);

    socket.emit('request_status');
    socket.emit('request_stats');

    return () => {
      socket.off('status_update', handleStatus);
      socket.off('stats_update', handleStats);
    };
  }, []);

  useEffect(() => {
    if (status.scene_running) {
      progressInterval.current = setInterval(async () => {
        try {
          const data = await api.getSceneProgress();
          
          if (data.scene_running) {
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
        } catch (e) {
          console.error(e);
        }
      }, 500);
    } else {
      if (progressInterval.current) clearInterval(progressInterval.current);
      setProgressData(prev => ({ ...prev, visible: false }));
    }

    return () => {
      if (progressInterval.current) clearInterval(progressInterval.current);
    };
  }, [status.scene_running]);

  const handleRunScene = async () => {
    try {
      const res = await fetch('/api/config/main_scene');
      const config = await res.json();
      const sceneName = config.json_file_name || 'intro.json';

      toast.promise(
        api.runScene(sceneName),
        {
            loading: 'Spúšťam hlavnú scénu...',
            success: 'Predstavenie spustené!',
            error: (err) => `Chyba: ${err.message}`
        }
      );
    } catch (e) {
      toast.error('Chyba pri načítaní konfigurácie: ' + e.message);
    }
  };

  const handleStopScene = async () => {
    if (await confirm({
        title: "Zastaviť scénu?",
        message: "Skutočne chcete zastaviť prebiehajúcu scénu? Toto okamžite preruší predstavenie.",
        confirmText: "Zastaviť",
        type: "danger"
    })) {
        toast.promise(
            api.stopScene(),
            {
                loading: 'Zastavujem...',
                success: 'Scéna zastavená (STOPALL)',
                error: (err) => `Chyba: ${err.message}`
            }
        );
    }
  };

  return (
    <div className="main-dashboard">
      <div className="system-status-card">
        <div className={`main-status ${status.scene_running ? 'running pulse' : (status.mqtt_connected ? 'ready' : 'error')}`}>
            <div className="status-icon">
                {status.scene_running ? '🎭' : (status.mqtt_connected ? '✅' : '⚠️')}
            </div>
            <div className="status-text">
                {status.scene_running ? 'Scéna prebieha' : (status.mqtt_connected ? 'Systém pripravený' : 'Systém nedostupný')}
            </div>
            <div className="status-description">
                {status.scene_running 
                    ? 'Predstavenie je v priebehu' 
                    : (status.mqtt_connected ? 'Môžete spustiť predstavenie' : 'Skontrolujte MQTT pripojenie')}
            </div>
        </div>
      </div>

      <div className="status-overview">
          <div className="status-item good">
              <div className="status-header">Miestnosť</div>
              <div className="status-value">{status.room_id}</div>
          </div>
          <div className={`status-item ${status.mqtt_connected ? 'good' : 'error'}`}>
              <div className="status-header">Komunikácia</div>
              <div className="status-value">
                  {status.mqtt_connected ? 'Pripojené' : 'Odpojené'}
              </div>
          </div>
          <div className={`status-item ${status.scene_running ? 'warning' : 'good'}`}>
              <div className="status-header">Scéna</div>
              <div className="status-value">
                  {status.scene_running ? 'Prebieha' : 'Pripravená'}
              </div>
          </div>
          <div className="status-item">
              <div className="status-header">Zariadenia</div>
              <div className="status-value">{deviceCount} pripojených</div>
          </div>
      </div>

      {progressData.visible && (
        <div className="scene-progress">
            <div className="progress-header">Prebieha scéna</div>
            <div className="progress-bar">
                <div 
                    className="progress-fill" 
                    style={{ width: `${progressData.progress}%` }}
                ></div>
            </div>
            <div className="progress-info">
                <span>{progressData.text}</span>
                <span>{progressData.info}</span>
            </div>
        </div>
      )}

      <div className="main-controls">
          {!status.scene_running ? (
            <button 
                className="main-scene-button" 
                onClick={handleRunScene}
                disabled={!status.mqtt_connected}
            >
                <div className="button-icon">▶️</div>
                <div className="button-text">Spustiť hlavnú scénu</div>
                <div className="button-subtext">Stlačte pre začatie predstavenia</div>
            </button>
          ) : (
            <button 
                className="stop-scene-button" 
                onClick={handleStopScene}
            >
                <div className="button-icon">⏹️</div>
                <div className="button-text">Zastaviť scénu</div>
                <div className="button-subtext">Núdzové zastavenie</div>
            </button>
          )}
      </div>
    </div>
  );
}