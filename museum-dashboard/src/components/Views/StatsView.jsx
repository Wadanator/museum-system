import { BarChart3, Clapperboard, Timer, Plug, ScrollText } from 'lucide-react';
import { useSystemStats } from '../../hooks/useSystemStats';
import PageHeader from '../ui/PageHeader';
import StatusBadge from '../ui/StatusBadge';
import Card from '../ui/Card'; // Použitie generickej karty
import StateNotice from '../ui/StateNotice';
import '../../styles/views/stats-view.css';

function basename(path) {
  return String(path || '').split(/[\\/]/).pop();
}

function sceneKey(path) {
  return basename(path).toLowerCase();
}

function SceneRoleBadges({ name, defaultScene, ambientScene }) {
  const normalizedName = sceneKey(name);
  const badges = [];

  if (defaultScene && normalizedName === sceneKey(defaultScene)) {
    badges.push({ label: 'D', title: 'Default scéna', className: 'default' });
  }
  if (ambientScene && normalizedName === sceneKey(ambientScene)) {
    badges.push({ label: 'A', title: 'Ambient scéna', className: 'ambient' });
  }

  if (badges.length === 0) return null;

  return (
    <div className="scene-role-badges" aria-label="Roly scény">
      {badges.map((badge) => (
        <span
          className={`scene-role-badge ${badge.className}`}
          title={badge.title}
          key={badge.label}
        >
          {badge.label}
        </span>
      ))}
    </div>
  );
}

export default function StatsView() {
  const {
    stats,
    sortedScenes,
    sortedDevices,
    formatTime,
    defaultScene,
    ambientScene
  } = useSystemStats();

  return (
    <div className="view-container">
      <PageHeader 
        title="Prehľad systému" 
        subtitle="Štatistiky a stav"
        icon={BarChart3} 
      />
      
      {/* KPI Karty - Špeciálny dizajn, nechávame div triedy */}
      <div className="stats-grid">
          <div className="stats-card primary-gradient">
              <div className="card-icon"><Clapperboard size={32} /></div>
              <div>
                  <h3>Spustení</h3>
                  <div className="stat-value white">{stats.total_scenes_played}</div>
              </div>
          </div>
          <div className="stats-card info-gradient">
              <div className="card-icon"><Timer size={32} /></div>
              <div>
                  <h3>Uptime</h3>
                  <div className="stat-value white">{formatTime(stats.total_uptime)}</div>
              </div>
          </div>
      </div>

      {/* Obsah - Tu už používame štandardné UI komponenty Card */}
      <div className="stats-content-grid">
          
          <Card title="Pripojené zariadenia" icon={Plug}>
              <div className="device-grid">
                  {sortedDevices.length === 0 ? (
                      <StateNotice
                        icon={Plug}
                        title="Žiadne zariadenia"
                        message="Zatiaľ nie sú dostupné žiadne pripojené zariadenia."
                        compact
                      />
                  ) : (
                      sortedDevices.map(([id, info]) => (
                        <div className={`device-card-item ${info.status.toLowerCase()}`} key={id}>
                            <div className="device-header">
                                <span className="device-name">{id}</span>
                                <StatusBadge status={info.status.toLowerCase()} label={info.status} />
                            </div>
                            <div className="device-meta">
                                {new Date(info.last_updated * 1000).toLocaleTimeString()}
                            </div>
                        </div>
                      ))
                  )}
              </div>
          </Card>
          
          <Card title="Top scény" icon={ScrollText}>
              <div className="scene-ranking-list">
                {sortedScenes.length === 0 ? (
                    <StateNotice
                      icon={ScrollText}
                      title="Žiadna aktivita"
                      message="Po spustení scén sa tu zobrazí ich používanie."
                      compact
                    />
                ) : (
                    sortedScenes.map(([name, count], index) => (
                        <div className="ranking-item" key={name}>
                            <div className="rank-number">{index + 1}.</div>
                            <div className="rank-info">
                                <div className="rank-title-row">
                                    <div className="rank-name">{name.replace('.json', '')}</div>
                                    <SceneRoleBadges
                                      name={name}
                                      defaultScene={defaultScene}
                                      ambientScene={ambientScene}
                                    />
                                </div>
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
          </Card>
      </div>
    </div>
  );
}
