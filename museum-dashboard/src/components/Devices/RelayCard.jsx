import { useState, useCallback } from 'react';
import { Power, PowerOff } from 'lucide-react';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import DeviceIcon from './DeviceIcon';
import { useDeviceControl } from '../../hooks/useDeviceControl';
import {
  getDeviceRuntimeLabel,
  getDeviceRuntimeTone,
} from '../../utils/deviceRuntimePresentation';

export default function RelayCard({ device, runtimeState }) {
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [isLoading, setIsLoading] = useState(false);
  const runtimeTone = getDeviceRuntimeTone(runtimeState);
  const runtimeLabel = getDeviceRuntimeLabel(runtimeState);
  const runtimeTopic = runtimeState?.entry?.topic || runtimeState?.topic || device.topic;

  const handleCommand = useCallback(async (command, displayText) => {
    setIsLoading(true);
    try {
      await sendCommand(command, displayText);
    } finally {
      setIsLoading(false);
    }
  }, [sendCommand]);

  return (
    <article className="device-control-row relay-card">
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
          </div>
        </div>
      </div>

      <div className="device-control-actions">
        <ButtonGroup>
          <Button
            variant="danger"
            onClick={() => handleCommand('OFF', 'VYPNUTÉ')}
            icon={PowerOff}
            isLoading={isLoading}
            className="device-command-button"
            aria-label={`Vypnúť ${device.name}`}
            title="Vypnúť"
            size="small"
          />
          <Button
            variant="success"
            onClick={() => handleCommand('ON', 'ZAPNUTÉ')}
            icon={Power}
            isLoading={isLoading}
            className="device-command-button"
            aria-label={`Zapnúť ${device.name}`}
            title="Zapnúť"
            size="small"
          />
        </ButtonGroup>
      </div>
    </article>
  );
}
