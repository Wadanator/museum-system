import { Drama, CheckCircle2, AlertTriangle, Play, Square, Loader2 } from 'lucide-react';
import Button from '../ui/Button';

function basename(path) {
  return String(path || '').split(/[\\/]/).pop();
}

export default function HeroCard({ status, onRun, onStop, isLoading }) {
  const isRunning = status.scene_running;
  const isConnected = status.mqtt_connected;
  const isAmbientMode = Boolean(status?.ambient?.enabled);
  const currentScene = basename(status?.current_scene_name);
  const ambientScene = basename(status?.ambient?.scene);
  const isAmbientSceneRunning = Boolean(
    isAmbientMode
    && isRunning
    && (!currentScene || currentScene === ambientScene)
  );
  const waitingForAmbientRestart = Boolean(isAmbientMode && status?.ambient?.next_restart_at);
  const disabled = !isConnected || isLoading || waitingForAmbientRestart;
  const runButtonText = isAmbientMode ? 'Zapnúť ambient' : 'Spustiť hlavnú scénu';
  const runButtonSubtext = isAmbientMode
    ? 'Spustiť ambient scénu'
    : 'Stlačte pre začatie predstavenia';
  const stopButtonText = isAmbientSceneRunning ? 'Zastaviť ambient' : 'Zastaviť scénu';
  const stopButtonSubtext = isAmbientSceneRunning ? 'Bezpečnostné zastavenie' : 'Núdzové zastavenie';

  let icon, title, desc, stateClass;

  if (isRunning) {
    icon = <Drama size={56} />;
    title = 'Scéna prebieha';
    desc = isAmbientSceneRunning ? 'Ambient scéna je aktívna' : 'Predstavenie je v priebehu';
    stateClass = 'running pulse';
  } else if (isConnected) {
    icon = <CheckCircle2 size={56} />;
    title = 'Systém pripravený';
    desc = isAmbientMode ? 'Môžete zapnúť ambient' : 'Môžete spustiť predstavenie';
    stateClass = 'ready';
  } else {
    icon = <AlertTriangle size={56} />;
    title = 'Systém nedostupný';
    desc = 'Skontrolujte MQTT pripojenie';
    stateClass = 'error';
  }

  return (
    <div className="hero-card">
      <div className={`main-status ${stateClass}`}>
        <div className="status-icon">{icon}</div>
        <div className="status-text">{title}</div>
        <div className="status-description">{desc}</div>
      </div>

      <div className="main-controls">
        {!isRunning ? (
          <Button
            variant="unstyled"
            className="main-scene-button"
            onClick={onRun}
            disabled={disabled}
            cooldown={0}
          >
            <div className="button-icon">
              {isLoading
                ? <Loader2 className="animate-spin" size={32} />
                : <Play size={32} fill="currentColor" />}
            </div>
            <div className="button-text">{runButtonText}</div>
            <div className="button-subtext">{runButtonSubtext}</div>
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
              {isLoading
                ? <Loader2 className="animate-spin" size={32} />
                : <Square size={32} fill="currentColor" />}
            </div>
            <div className="button-text">{stopButtonText}</div>
            <div className="button-subtext">{stopButtonSubtext}</div>
          </Button>
        )}
      </div>
    </div>
  );
}
