import { useState, useEffect, useMemo } from 'react';
import { socket } from '../../services/socket';
import { BarChart3, Clapperboard, Timer, Plug, ScrollText } from 'lucide-react';
import PageHeader from '../ui/PageHeader';
import StatusBadge from '../ui/StatusBadge';
import '../../styles/views/stats-view.css';

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

  const formatTime = (s) => `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;

  const sortedScenes = useMemo(() => Object.entries(stats.scene_play_counts || {}).sort(([, a], [, b]) => b - a), [stats.scene_play_counts]);
  const sortedDevices = useMemo(() => Object.entries(stats.connected_devices || {}).sort(([, a], [, b]) => (a.status === 'online' ? -1 : 1)), [stats.connected_devices]);

  return (
    <div className="tab-content active">
      {/* Nový Header */}
      <PageHeader 
        title="Prehľad systému" 
        subtitle="Štatistiky a stav"
        icon={BarChart3} 
      />
      
      <div className="stats-grid">
          <div className="stats-card primary-gradient">
              <div className="card-icon"><Clapperboard size={32} /></div>
              <div><h3>Spustení</h3><div className="stat-value white">{stats.total_scenes_played}</div></div>
          </div>
          <div className="stats-card info-gradient">
              <div className="card-icon"><Timer size={32} /></div>
              <div><h3>Uptime</h3><div className="stat-value white">{formatTime(stats.total_uptime)}</div></div>
          </div>
      </div>

      <div className="stats-content-grid">
          <div className="stats-column">
              <h3><Plug size={20} style={{verticalAlign:'middle'}}/> Pripojené zariadenia</h3>
              <div className="device-grid">
                  {sortedDevices.length === 0 ? <div className="empty-message">Žiadne zariadenia</div> : 
                      sortedDevices.map(([id, info]) => (
                        <div className={`device-card ${info.status.toLowerCase()}`} key={id}>
                            <div className="device-header">
                                <span className="device-name">{id}</span>
                                <StatusBadge status={info.status.toLowerCase()} label={info.status} />
                            </div>
                            <small>{new Date(info.last_updated * 1000).toLocaleTimeString()}</small>
                        </div>
                      ))
                  }
              </div>
          </div>
          
          <div className="stats-column">
              <h3><ScrollText size={20} style={{verticalAlign:'middle'}}/> Top scény</h3>
              <div className="scene-ranking-list">
                {sortedScenes.length === 0 ? <div className="empty-message">Žiadna aktivita</div> :
                    sortedScenes.map(([name, count], index) => (
                        <div className="ranking-item" key={name}>
                            <div className="rank-number">{index + 1}.</div>
                            <div className="rank-info">
                                <div className="rank-name">{name.replace('.json', '')}</div>
                                <div className="rank-bar-container"><div className="rank-bar" style={{width: `${Math.min((count / sortedScenes[0][1]) * 100, 100)}%`}}></div></div>
                            </div>
                            <div className="rank-count">{count}x</div>
                        </div>
                    ))
                }
              </div>
          </div>
      </div>
    </div>
  );
}