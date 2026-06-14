import { FileText, Loader2, RotateCw, Wifi, WifiOff } from 'lucide-react';
import Button from '../ui/Button';

function basename(path) {
  return String(path || '-').split(/[\\/]/).pop();
}

function getAmbientState(status) {
  const ambient = status?.ambient;
  if (!ambient?.enabled) return null;

  const currentScene = status?.current_scene_name || '';
  const ambientScene = ambient.scene || '';
  const sceneRunning = Boolean(status?.scene_running);
  const ambientRunning = sceneRunning && (
    !currentScene || basename(currentScene) === basename(ambientScene)
  );

  if (ambientRunning) return { label: 'Beží', className: 'good' };
  if (sceneRunning) return { label: 'Iná scéna', className: 'warning' };
  if (ambient.suspended) return { label: 'Vypnutý', className: 'warning' };
  if (ambient.next_restart_at) return { label: 'Čaká', className: 'warning' };
  return { label: 'Pripravený', className: 'good' };
}

export default function StatsGrid({ status, deviceCount, onResume, isLoading }) {
  const ambientState = getAmbientState(status);
  const ambient = status?.ambient;
  const defaultScene = basename(status?.default_scene);
  const ambientScene = basename(ambient?.scene);
  const canResumeAmbient = Boolean(
    ambient?.enabled
    && !status?.scene_running
    && !ambient?.next_restart_at
    && status?.mqtt_connected
    && !isLoading
  );

  return (
    <div className="status-overview">
      <div className={`status-item ${status.room_id && status.room_id !== '-' && status.room_id !== 'Unknown' ? 'good' : 'error'}`}>
        <div className="status-header">Miestnosť</div>
        <div className="status-value">{status.room_id}</div>
      </div>

      <div className={`status-item ${status.mqtt_connected ? 'good' : 'error'}`}>
        <div className="status-header">Komunikácia</div>
        <div className="status-value status-value-row">
          {status.mqtt_connected
            ? <><Wifi size={20} /> Pripojené</>
            : <><WifiOff size={20} /> Odpojené</>}
        </div>
      </div>

      <div className={`status-item ${deviceCount === 0 ? 'error' : 'good'}`}>
        <div className="status-header">Zariadenia</div>
        <div className="status-value">{deviceCount} pripojených</div>
      </div>

      <div className="status-item neutral scene-status">
        <div className="status-header">Hlavná scéna</div>
        <div className="status-value status-value-file" title={defaultScene}>
          <FileText size={18} />
          {defaultScene}
        </div>
      </div>

      {ambient?.enabled && (
        <div className={`status-item ${ambientState.className} scene-status ambient-stat`}>
          <div className="status-header">Ambient</div>
          <div className="status-value status-value-file" title={ambientScene}>
            <FileText size={18} />
            {ambientScene}
          </div>
          <div className="status-subrow">
            <span>{ambientState.label}</span>
            {!status?.scene_running && (
              <Button
                variant="unstyled"
                className="ambient-stat-button"
                onClick={onResume}
                disabled={!canResumeAmbient}
                cooldown={0}
                title="Zapnúť ambient"
                aria-label="Zapnúť ambient"
              >
                {isLoading
                  ? <Loader2 className="animate-spin" size={16} />
                  : <RotateCw size={16} />}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
