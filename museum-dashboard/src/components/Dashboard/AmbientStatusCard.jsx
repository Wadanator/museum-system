import { Clock3, Loader2, Play, Radio, RotateCw, Square } from 'lucide-react';
import Button from '../ui/Button';

const OUTCOME_LABELS = {
  never_started: 'ešte nebežala',
  normal_end: 'dobehla',
  error: 'chyba',
  missing_scene: 'chýba súbor',
  load_failure: 'chyba načítania',
  parser_unavailable: 'parser nedostupný',
  start_failure: 'štart zlyhal',
  explicit_stop: 'zastavená',
  shutdown: 'vypnutie'
};

function basename(path) {
  return String(path || '').split(/[\\/]/).pop();
}

function formatRestartTime(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString('sk-SK', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

export default function AmbientStatusCard({ status, onResume, isLoading }) {
  const ambient = status?.ambient;
  if (!ambient?.enabled) return null;

  const sceneName = ambient.scene || '-';
  const currentScene = status?.current_scene_name || '';
  const isSceneRunning = Boolean(status?.scene_running);
  const isAmbientSceneRunning = isSceneRunning && (
    !currentScene || basename(currentScene) === basename(sceneName)
  );
  const nextRestartTime = formatRestartTime(ambient.next_restart_at);
  const isWaiting = Boolean(nextRestartTime);
  const isConnected = Boolean(status?.mqtt_connected);
  const canResume = !isLoading && isConnected && !isSceneRunning && !isWaiting;

  let Icon = Radio;
  let stateClass = 'ready';
  let title = 'Ambient pripravený';
  let description = sceneName;

  if (isAmbientSceneRunning) {
    Icon = Radio;
    stateClass = 'running';
    title = 'Ambient beží';
  } else if (isSceneRunning) {
    Icon = Square;
    stateClass = 'blocked';
    title = 'Beží iná scéna';
    description = currentScene || sceneName;
  } else if (ambient.suspended) {
    Icon = Play;
    stateClass = 'suspended';
    title = 'Ambient je vypnutý';
  } else if (isWaiting) {
    Icon = Clock3;
    stateClass = 'waiting';
    title = 'Ambient čaká';
    description = `Ďalší štart ${nextRestartTime}`;
  }

  const outcomeLabel = OUTCOME_LABELS[ambient.last_outcome] || ambient.last_outcome || '-';

  return (
    <section className={`ambient-card ${stateClass}`}>
      <div className="ambient-card-main">
        <div className="ambient-card-icon">
          <Icon size={24} />
        </div>
        <div className="ambient-card-copy">
          <div className="ambient-card-kicker">Ambient mód</div>
          <div className="ambient-card-title">{title}</div>
          <div className="ambient-card-scene">{description}</div>
        </div>
      </div>

      <div className="ambient-card-meta">
        <div>
          <span>Scéna</span>
          <strong>{sceneName}</strong>
        </div>
        <div>
          <span>Výsledok</span>
          <strong>{outcomeLabel}</strong>
        </div>
      </div>

      {!isAmbientSceneRunning && (
        <Button
          variant="success"
          className="ambient-resume-button"
          onClick={onResume}
          disabled={!canResume}
          cooldown={0}
        >
          {isLoading ? <Loader2 className="animate-spin" size={18} /> : <RotateCw size={18} />}
          Zapnúť ambient
        </Button>
      )}
    </section>
  );
}
