import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, Clock, RefreshCw, Zap } from 'lucide-react';
import Button from '../ui/Button';
import { useRuntime } from '../../context/useRuntime';

const formatSyncTime = (timestamp) => {
  if (!timestamp) return '--:--';
  return new Date(timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export default function RuntimeStatusBar() {
  const {
    sceneRunning,
    currentSceneName,
    activeState,
    runtimeSummary,
    status,
    lastRuntimeSync,
    refreshRuntime,
  } = useRuntime();

  const sceneLabel = sceneRunning
    ? (currentSceneName || 'Scena bezi')
    : 'Idle';
  const activeLabel = sceneRunning
    ? (activeState || 'START')
    : '---';
  const hasWarnings = runtimeSummary.pending > 0
    || runtimeSummary.stale > 0
    || !status.mqtt_connected;

  return (
    <section className={`runtime-status-bar ${sceneRunning ? 'is-running' : ''}`}>
      <Link to="/live" className="runtime-status-main">
        <span className={`runtime-status-dot ${sceneRunning ? 'pulse' : ''}`} />
        <span className="runtime-status-title">
          <Activity size={16} />
          {sceneLabel}
        </span>
        <span className="runtime-status-state">
          STAV: {activeLabel}
        </span>
      </Link>

      <div className="runtime-status-metrics">
        <span className="runtime-metric is-on">
          <Zap size={14} />
          ON {runtimeSummary.on}
        </span>
        <span className="runtime-metric">
          OFF {runtimeSummary.off}
        </span>
        {(runtimeSummary.unknown > 0 || runtimeSummary.pending > 0 || runtimeSummary.stale > 0) && (
          <span className={`runtime-metric ${hasWarnings ? 'is-warning' : ''}`}>
            <AlertTriangle size={14} />
            {runtimeSummary.pending > 0
              ? `PENDING ${runtimeSummary.pending}`
              : `UNKNOWN ${runtimeSummary.unknown}`}
          </span>
        )}
        <span className="runtime-metric">
          <Clock size={14} />
          {formatSyncTime(lastRuntimeSync)}
        </span>
        <Button
          variant="toolbar"
          size="small"
          icon={RefreshCw}
          onClick={refreshRuntime}
          title="Obnovit runtime"
          aria-label="Obnovit runtime"
        />
      </div>
    </section>
  );
}
