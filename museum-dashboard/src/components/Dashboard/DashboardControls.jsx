import { Play, Square } from 'lucide-react';

export default function DashboardControls({ status, onRun, onStop }) {
  // Používame pôvodné CSS triedy pre zachovanie "veľkého" vzhľadu,
  // ale kód je teraz pekne izolovaný.
  
  return (
      <div className="main-controls">
          {!status.scene_running ? (
            <button 
                className="main-scene-button" 
                onClick={onRun}
                disabled={!status.mqtt_connected}
            >
                <div className="button-icon"><Play size={32} fill="currentColor" /></div>
                <div className="button-text">Spustiť hlavnú scénu</div>
                <div className="button-subtext">Stlačte pre začatie predstavenia</div>
            </button>
          ) : (
            <button 
                className="stop-scene-button" 
                onClick={onStop}
            >
                <div className="button-icon"><Square size={32} fill="currentColor" /></div>
                <div className="button-text">Zastaviť scénu</div>
                <div className="button-subtext">Núdzové zastavenie</div>
            </button>
          )}
      </div>
  );
}