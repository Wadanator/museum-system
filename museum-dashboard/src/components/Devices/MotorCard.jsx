import { useState } from 'react';
import { Rewind, FastForward, Square } from 'lucide-react';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import StatusBadge from '../ui/StatusBadge';
import DeviceIcon from './DeviceIcon';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import {
  getDeviceRuntimeLabel,
  getDeviceRuntimeTone,
} from '../../utils/deviceRuntimePresentation';

export default function MotorCard({ device, runtimeState }) {
  const speed = device.speed || 100;
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [loading, setLoading] = useState(false);
  const runtimeTone = getDeviceRuntimeTone(runtimeState);
  const runtimeLabel = getDeviceRuntimeLabel(runtimeState);
  const runtimeTopic = runtimeState?.entry?.topic || runtimeState?.topic || device.topic;

  const handleAction = async (direction, label) => {
    if (loading) return;

    setLoading(true);

    let payload = 'OFF';
    if (direction === 'LEFT') payload = `ON:${speed}:L`;
    else if (direction === 'RIGHT') payload = `ON:${speed}:R`;

    try {
      await sendCommand(payload, label);
    } finally {
      setLoading(false);
    }
  };

  return (
    <article className="device-control-row motor-card">
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
            onClick={() => handleAction('LEFT', 'Vzad')}
            icon={Rewind}
            isLoading={loading}
            className="device-command-button"
            aria-label={`Spustiť ${device.name} vzad`}
            title="Vzad"
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
            onClick={() => handleAction('RIGHT', 'Vpred')}
            icon={FastForward}
            isLoading={loading}
            className="device-command-button"
            aria-label={`Spustiť ${device.name} vpred`}
            title="Vpred"
            size="small"
          />
        </ButtonGroup>
      </div>
    </article>
  );
}
