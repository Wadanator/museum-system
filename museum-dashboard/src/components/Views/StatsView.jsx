import { useState, useEffect, useMemo } from 'react';
import { socket } from '../../services/socket';

export default function StatsView() {
  const [stats, setStats] = useState({
    total_scenes_played: 0,
    total_uptime: 0,
    connected_devices: {},
    scene_play_counts: {}
  });

  useEffect(() => {
    socket.emit('request_stats');
    const handleStats = (data) => setStats(data);
    socket.on('stats_update', handleStats);
    return () => socket.off('stats_update', handleStats);
  }, []);

  const formatTime = (seconds) => {
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      return `${h}h ${m}m`;
  };

  // Zoraď scény podľa počtu spustení (najviac navrchu)
  const sortedScenes = useMemo(() => {
    return Object.entries(stats.scene_play_counts || {})
        .sort(([, countA], [, countB]) => countB - countA);
  }, [stats.scene_play_counts]);

  // Zoraď zariadenia (online prvé)
  const sortedDevices = useMemo(() => {
    return Object.entries(stats.connected_devices || {})
        .sort(([, infoA], [, infoB]) => {
            if (infoA.status === 'online' && infoB.status !== 'online') return -1;
            if (infoA.status !== 'online' && infoB.status === 'online') return 1;
            return 0;
        });
  }, [stats.connected_devices]);

  return (
    <div className="tab-content active">
      <div style={{marginBottom: '24px'}}>
        <h2>📊 Prehľad systému</h2>
        <p style={{color: '#6b7280'}}>Detailné metriky výkonu a pripojení</p>
      </div>
      
      {/* HLAVNÉ KARTY */}
      <div className="stats-grid">
          <div className="stats-card primary-gradient">
              <div className="card-icon">🎬</div>
              <div>
                <h3>Celkovo spustení</h3>
                <div className="stat-value white">{stats.total_scenes_played}</div>
              </div>
          </div>
          <div className="stats-card info-gradient">
              <div className="card-icon">⏱️</div>
              <div>
                <h3>Čas prevádzky</h3>
                <div className="stat-value white">{formatTime(stats.total_uptime)}</div>
              </div>
          </div>
      </div>

      {/* ROZLOŽENIE DO DVOCH STĹPCOV */}
      <div className="stats-content-grid">
          
          {/* ĽAVÝ STĹPEC: ZARIADENIA */}
          <div className="stats-column">
              <h3 style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  🔌 Pripojené zariadenia
                  <span className="badge">{sortedDevices.length}</span>
              </h3>
              
              <div className="device-grid">
                  {sortedDevices.length === 0 ? (
                      <div className="empty-message">Žiadne zariadenia</div>
                  ) : (
                      sortedDevices.map(([id, info]) => (
                        <div className={`device-card ${info.status.toLowerCase()}`} key={id}>
                            <div className="device-header">
                                <span className="device-name">{id}</span>
                                <span className={`status-indicator ${info.status.toLowerCase()}`}></span>
                            </div>
                            <div className="device-meta">
                                {info.status === 'online' ? '🟢 Online' : '🔴 Offline'}
                                <br/>
                                <small>{new Date(info.last_updated * 1000).toLocaleTimeString()}</small>
                            </div>
                        </div>
                      ))
                  )}
              </div>
          </div>
          
          {/* PRAVÝ STĹPEC: TOP SCÉNY */}
          <div className="stats-column">
              <h3>📜 Top scény</h3>
              <div className="scene-ranking-list">
                {sortedScenes.length === 0 ? (
                    <div className="empty-message">Zatiaľ žiadna aktivita</div>
                ) : (
                    sortedScenes.map(([name, count], index) => (
                        <div className="ranking-item" key={name}>
                            <div className="rank-number">{index + 1}.</div>
                            <div className="rank-info">
                                <div className="rank-name">{name.replace('.json', '')}</div>
                                <div className="rank-bar-container">
                                    <div 
                                        className="rank-bar" 
                                        style={{width: `${Math.min((count / sortedScenes[0][1]) * 100, 100)}%`}}
                                    ></div>
                                </div>
                            </div>
                            <div className="rank-count">{count}x</div>
                        </div>
                    ))
                )}
              </div>
          </div>

      </div>
    </div>
  );
}