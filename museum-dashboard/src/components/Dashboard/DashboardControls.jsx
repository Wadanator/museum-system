import { Play, Square, Loader2 } from 'lucide-react';
import Button from '../ui/Button';

export default function DashboardControls({ status, onRun, onStop, isLoading }) {
  const disabled = !status.mqtt_connected || isLoading;

  return (
      <div className="main-controls">
          {!status.scene_running ? (
            <Button
                variant="unstyled"
                className="main-scene-button" 
                onClick={onRun}
                disabled={disabled}
                cooldown={0}
            >
                {/* Ikona sa zmení na loader ak načítava */}
                <div className="button-icon">
                    {isLoading ? <Loader2 className="animate-spin" size={32} /> : <Play size={32} fill="currentColor" />}
                </div>
                <div className="button-text">Spustiť hlavnú scénu</div>
                <div className="button-subtext">Stlačte pre začatie predstavenia</div>
                        </Button>
          ) : (
                        <Button
                            variant="unstyled"
                className="stop-scene-button" 
                onClick={onStop}
                disabled={isLoading}
                                cooldown={0}
            >
                <div className="button-icon">
                    {isLoading ? <Loader2 className="animate-spin" size={32} /> : <Square size={32} fill="currentColor" />}
                </div>
                <div className="button-text">Zastaviť scénu</div>
                <div className="button-subtext">Núdzové zastavenie</div>
                        </Button>
          )}
      </div>
  );
}