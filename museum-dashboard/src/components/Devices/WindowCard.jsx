import { useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, Square } from 'lucide-react';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import StatusBadge from '../ui/StatusBadge';
import DeviceIcon from './DeviceIcon';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import {
  getDeviceRuntimeLabel,
  getDeviceRuntimeTone,
} from '../../utils/deviceRuntimePresentation';
import { buildWindowCommand, normalizeWindowSpeed } from '../../utils/deviceCommands';

export default function WindowCard({ device, runtimeState }) {
  const speed = normalizeWindowSpeed(device.speed);
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [loading, setLoading] = useState(false);
  const runtimeTone = getDeviceRuntimeTone(runtimeState);
  const runtimeLabel = getDeviceRuntimeLabel(runtimeState);
  const runtimeTopic = runtimeState?.entry?.topic || runtimeState?.topic || device.topic;

  const handleAction = async (action, label) => {
    if (loading) return;

    setLoading(true);
    try {
      await sendCommand(buildWindowCommand(action, speed), label);
    } finally {
      setLoading(false);
    }
  };

  return (
    <article className="device-control-row window-card">
      <div className="device-control-main">
        <div
          className={`device-control-icon device-control-icon--${runtimeTone}`}
          title={`${runtimeTopic}: ${runtimeLabel}`}
          aria-label={`Stav zariadenia ${runtimeLabel}`}
        >
          <DeviceIcon device={device} size={22} />
        </div>

        <div className="device-control-text">
          <h4 className="device-control-title">{device.name}</h4>
          <div className="device-control-meta">
            <span className="device-control-topic">{device.topic}</span>
            <StatusBadge status="info" label={`${speed}%`} />
          </div>
        </div>
      </div>

      <div className="device-control-actions">
        <ButtonGroup>
          <Button
            variant="success"
            onClick={() => handleAction('OPEN', 'Otváranie')}
            icon={ArrowUpFromLine}
            isLoading={loading}
            className="device-command-button"
            aria-label={`Otvoriť ${device.name}`}
            title="Otvoriť"
            size="small"
          />

          <Button
            variant="danger"
            onClick={() => handleAction('STOP', 'Stop')}
            icon={Square}
            isLoading={loading}
            className="device-command-button"
            aria-label={`Zastaviť ${device.name}`}
            title="STOP"
            size="small"
          />

          <Button
            variant="success"
            onClick={() => handleAction('CLOSE', 'Zatváranie')}
            icon={ArrowDownToLine}
            isLoading={loading}
            className="device-command-button"
            aria-label={`Zatvoriť ${device.name}`}
            title="Zatvoriť"
            size="small"
          />
        </ButtonGroup>
      </div>
    </article>
  );
}
