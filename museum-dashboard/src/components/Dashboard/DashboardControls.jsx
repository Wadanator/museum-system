import { Play, Square, Loader2 } from 'lucide-react';

export default function DashboardControls({ status, onRun, onStop, isLoading }) {
  const disabled = !status.mqtt_connected || isLoading;

  return (
      <div className="main-controls">
          {!status.scene_running ? (
            <button 
                className="main-scene-button" 
                onClick={onRun}
                disabled={disabled}
                style={{ opacity: disabled ? 0.7 : 1, cursor: disabled ? 'not-allowed' : 'pointer' }}
            >
                {/* Ikona sa zmení na loader ak načítava */}
                <div className="button-icon">
                    {isLoading ? <Loader2 className="animate-spin" size={32} /> : <Play size={32} fill="currentColor" />}
                </div>
                <div className="button-text">Spustiť hlavnú scénu</div>
                <div className="button-subtext">Stlačte pre začatie predstavenia</div>
            </button>
          ) : (
            <button 
                className="stop-scene-button" 
                onClick={onStop}
                disabled={isLoading}
                style={{ opacity: isLoading ? 0.7 : 1, cursor: isLoading ? 'not-allowed' : 'pointer' }}
            >
                <div className="button-icon">
                    {isLoading ? <Loader2 className="animate-spin" size={32} /> : <Square size={32} fill="currentColor" />}
                </div>
                <div className="button-text">Zastaviť scénu</div>
                <div className="button-subtext">Núdzové zastavenie</div>
            </button>
          )}
      </div>
  );
}