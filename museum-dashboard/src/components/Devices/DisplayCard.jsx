import { useMemo, useState } from 'react';
import { Monitor, Power, PowerOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '../../services/api';
import { useRuntime } from '../../context/useRuntime';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import StatusBadge from '../ui/StatusBadge';

const stateToTone = (displayStatus) => {
  if (!displayStatus?.available || !displayStatus?.enabled) return 'unknown';

  const requestedState = String(displayStatus.requested_state || '').toLowerCase();
  if (requestedState === 'on') return 'on';
  if (requestedState === 'standby' || requestedState === 'off') return 'off';
  return 'unknown';
};

const stateToLabel = (displayStatus) => {
  if (!displayStatus?.available) return 'NEDOSTUPNY';
  if (!displayStatus?.enabled) return 'VYPNUTE';

  const requestedState = String(displayStatus.requested_state || '').toLowerCase();
  if (requestedState === 'on') return 'ON';
  if (requestedState === 'standby' || requestedState === 'off') return 'STANDBY';
  return 'UNKNOWN';
};

const stateToBadge = (tone) => {
  if (tone === 'on') return 'success';
  if (tone === 'off') return 'danger';
  return 'info';
};

export default function DisplayCard() {
  const { status, refreshRuntime } = useRuntime();
  const [loadingAction, setLoadingAction] = useState(null);
  const displayStatus = status?.display || null;
  const roomId = status?.room_id && status.room_id !== '-' ? status.room_id : 'room1';
  const topic = displayStatus?.topic || `${roomId}/display`;
  const runtimeTone = stateToTone(displayStatus);
  const runtimeLabel = stateToLabel(displayStatus);
  const canControl = Boolean(displayStatus?.available && displayStatus?.enabled);

  const detailTitle = useMemo(() => {
    const backend = displayStatus?.backend || 'none';
    const reasons = Array.isArray(displayStatus?.active_reasons)
      ? displayStatus.active_reasons.join(', ')
      : '';
    return `${topic}: ${runtimeLabel} (${backend}${reasons ? `, ${reasons}` : ''})`;
  }, [displayStatus, runtimeLabel, topic]);

  const handleDisplayAction = async (action) => {
    if (loadingAction) return;

    setLoadingAction(action);
    const isOn = action === 'on';
    const toastId = toast.loading(isOn ? 'Zapínam monitor...' : 'Vypínam monitor...');

    try {
      const result = isOn ? await api.displayOn() : await api.displayOff();
      if (result?.success === false) {
        throw new Error(result?.error || 'Display command failed');
      }

      await refreshRuntime();
      toast.success(isOn ? 'Monitor sa zapína.' : 'Monitor ide do standby.', { id: toastId });
    } catch (e) {
      console.error('Display control error:', e);
      toast.error(e.message || 'Nepodarilo sa ovládať monitor.', { id: toastId });
      await refreshRuntime();
    } finally {
      setLoadingAction(null);
    }
  };

  return (
    <article className="device-control-row window-card display-control-card">
      <div className="device-control-main">
        <div
          className={`device-control-icon device-control-icon--${runtimeTone}`}
          title={detailTitle}
          aria-label={`Stav monitora ${runtimeLabel}`}
        >
          <Monitor size={22} />
        </div>

        <div className="device-control-text">
          <h4 className="device-control-title">Monitor</h4>
          <div className="device-control-meta">
            <span className="device-control-topic">{topic}</span>
            <StatusBadge status={stateToBadge(runtimeTone)} label={runtimeLabel} />
          </div>
        </div>
      </div>

      <div className="device-control-actions">
        <ButtonGroup>
          <Button
            variant="success"
            onClick={() => handleDisplayAction('on')}
            icon={Power}
            isLoading={loadingAction === 'on'}
            disabled={!canControl}
            className="device-command-button"
            aria-label="Zapnut monitor"
            title="Zapnut monitor"
            size="small"
          />

          <Button
            variant="danger"
            onClick={() => handleDisplayAction('off')}
            icon={PowerOff}
            isLoading={loadingAction === 'off'}
            disabled={!canControl}
            className="device-command-button"
            aria-label="Vypnut monitor"
            title="Vypnut monitor"
            size="small"
          />
        </ButtonGroup>
      </div>
    </article>
  );
}
