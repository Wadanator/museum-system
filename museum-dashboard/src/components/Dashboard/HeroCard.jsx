import { Drama, CheckCircle2, AlertTriangle, Play, Square, Loader2 } from 'lucide-react';

export default function HeroCard({ status, onRun, onStop, isLoading }) {
  const isRunning = status.scene_running;
  const isConnected = status.mqtt_connected;
  const disabled = !isConnected || isLoading;

  let icon, title, desc, stateClass;

  if (isRunning) {
    icon = <Drama size={56} />;
    title = 'Scéna prebieha';
    desc = 'Predstavenie je v priebehu';
    stateClass = 'running pulse';
  } else if (isConnected) {
    icon = <CheckCircle2 size={56} />;
    title = 'Systém pripravený';
    desc = 'Môžete spustiť predstavenie';
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
          <button
            className="main-scene-button"
            onClick={onRun}
            disabled={disabled}
          >
            <div className="button-icon">
              {isLoading
                ? <Loader2 className="animate-spin" size={32} />
                : <Play size={32} fill="currentColor" />}
            </div>
            <div className="button-text">Spustiť hlavnú scénu</div>
            <div className="button-subtext">Stlačte pre začatie predstavenia</div>
          </button>
        ) : (
          <button
            className="stop-scene-button"
            onClick={onStop}
            disabled={isLoading}
          >
            <div className="button-icon">
              {isLoading
                ? <Loader2 className="animate-spin" size={32} />
                : <Square size={32} fill="currentColor" />}
            </div>
            <div className="button-text">Zastaviť scénu</div>
            <div className="button-subtext">Núdzové zastavenie</div>
          </button>
        )}
      </div>
    </div>
  );
}