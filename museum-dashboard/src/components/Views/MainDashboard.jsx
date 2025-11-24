// Súbor: museum-dashboard/src/components/Views/MainDashboard.jsx (Zmenený)
import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { useSocket } from '../../context/SocketContext';
import toast from 'react-hot-toast';

export default function MainDashboard() {
  const { isAuthenticated } = useAuth();
  const socket = useSocket(); // ZMENA 1: Získanie SocketIO inštancie
  
  const [status, setStatus] = useState({ 
    room_id: '...', 
    scene_running: false, 
    mqtt_connected: false,
    uptime: 'Neznámy',
    log_count: 0
  });
  
  // ZMENA 2: Stav na uloženie progresu prichádzajúceho cez Socket.IO
  const [sceneProgress, setSceneProgress] = useState(null); 
  
  // Stiahne základné status informácie (ktoré sú stále cez HTTP GET)
  const loadStatus = async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
    } catch (error) {
      console.error(error);
    }
  };

  const handleStopScene = async () => {
    toast.promise(
      api.stopScene(),
      {
        loading: 'Zastavujem scénu...',
        success: (res) => {
          if (res.success) {
            // Po úspešnom STOPALL môžeme manuálne vynútiť stav neaktívnej scény
            setStatus(prev => ({ ...prev, scene_running: false }));
            setSceneProgress(null); // Vynulujeme progres
            return 'Scéna úspešne zastavená a STOPALL vykonaný';
          } else {
            return `Chyba pri zastavení: ${res.error}`;
          }
        },
        error: (err) => `Chyba komunikácie: ${err.message}`
      }
    );
  };
  
  useEffect(() => {
    if (!isAuthenticated || !socket) return;

    // Inicializačný fetch statusu (vrátane scene_running)
    loadStatus();

    // ===================================================================
    // ZMENA 3: Odstránenie pollingu a nahradenie Socket.IO listenerom
    // ===================================================================

    // Listener na aktualizácie progresu (PUSH model)
    const handleProgressUpdate = (data) => {
      setSceneProgress(data);
      // Tiež aktualizujeme hlavný status
      setStatus(prev => ({ ...prev, scene_running: data.scene_running }));
    };

    // Socket.IO event pre progres
    socket.on('scene_progress_update', handleProgressUpdate);
    
    // Socket.IO event pre status (môže byť emitovaný iným procesom)
    socket.on('status_update', (data) => {
      setStatus(data);
    });

    // Cleanup funkcia
    return () => {
      // Odstránenie listenerov
      socket.off('scene_progress_update', handleProgressUpdate);
      socket.off('status_update');
    };
  }, [isAuthenticated, socket]);

  // Pomocná funkcia pre vizuálne zobrazenie progresu
  const renderSceneProgress = () => {
    if (!status.scene_running && (!sceneProgress || sceneProgress.current_state === 'END' || sceneProgress.mode === 'none')) {
      return <div className="scene-status inactive">Scéna nie je spustená</div>;
    }

    if (sceneProgress && sceneProgress.mode === 'state_machine') {
      const completionPercentage = Math.round(sceneProgress.progress * 100);
      const stateInfo = `${sceneProgress.states_completed} / ${sceneProgress.total_states}`;
      const timeInfo = `${sceneProgress.scene_elapsed}s (stav: ${sceneProgress.state_elapsed}s)`;
      
      return (
        <div className="scene-status active state-machine">
          <h3>🎭 Scéna: {sceneProgress.scene_id}</h3>
          <p>Stav: <span className="highlight-green">{sceneProgress.current_state}</span></p>
          <p>Popis: {sceneProgress.state_description || 'N/A'}</p>
          
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${completionPercentage}%` }}></div>
            <span className="progress-text">{completionPercentage}%</span>
          </div>
          <p className="small-meta">Stavové prechody: {stateInfo} | Celkový čas: {timeInfo}</p>
        </div>
      );
    }
    
    // Predvolené zobrazenie, ak beží, ale progres nie je k dispozícii (napr. pri inicializácii)
    return <div className="scene-status active">Scéna je spustená, čakám na dáta o progrese...</div>;
  };

  if (!isAuthenticated) {
    return (
      <div className="tab-content active">
        <p className="empty-state-text">Pre zobrazenie dashboardu sa musíte prihlásiť.</p>
      </div>
    );
  }

  return (
    <div className="tab-content active main-dashboard">
      <h2>🏠 Hlavný Dashboard</h2>
      
      {/* Sekcia Progres Scény */}
      <div className="card full-width">
        <div className="card-header">
          <h3>Stav Spustenej Scény</h3>
          {status.scene_running && (
            <button className="btn btn-danger btn-small" onClick={handleStopScene}>
              ⏹️ Zastaviť scénu
            </button>
          )}
        </div>
        <div className="card-content">
          {renderSceneProgress()}
        </div>
      </div>

      {/* Systémové Metriky */}
      <div className="layout-grid grid-3">
        <div className="card system-metric">
          <h4>Room ID</h4>
          <p className="metric-value">{status.room_id}</p>
        </div>
        <div className="card system-metric">
          <h4>MQTT Broker</h4>
          <p className={`metric-value ${status.mqtt_connected ? 'text-green' : 'text-red'}`}>
            {status.mqtt_connected ? 'Pripojený' : 'Odpojený'}
          </p>
        </div>
        <div className="card system-metric">
          <h4>Uptime</h4>
          <p className="metric-value">{status.uptime}</p>
        </div>
      </div>
      
      {/* Odkaz na logy */}
      <div className="card full-width">
        <div className="card-content" style={{textAlign: 'center'}}>
          <p>Systémový log obsahuje <span className="highlight-blue">{status.log_count}</span> záznamov.</p>
        </div>
      </div>
    </div>
  );
}