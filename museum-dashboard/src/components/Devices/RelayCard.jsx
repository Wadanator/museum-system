import { useState, useCallback } from 'react';
import { Power, PowerOff } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import DeviceIcon, { getDeviceIconComponent } from './DeviceIcon';
import DeviceRuntimeIndicator from './DeviceRuntimeIndicator';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function RelayCard({ device, runtimeState }) {
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [isLoading, setIsLoading] = useState(false);

  // Ikona v hlavičke karty
  const HeaderIcon = getDeviceIconComponent(device);
  
  // Veľká ikona v strede (ak nie je definovaná v configu, dáme default)

  const handleCommand = useCallback(async (command, displayText) => {
    setIsLoading(true);
    try {
      await sendCommand(command, displayText);
    } finally {
      setIsLoading(false);
    }
  }, [sendCommand]);

  return (
    <Card 
      title={device.name} 
      icon={HeaderIcon} 
      actions={<DeviceRuntimeIndicator runtimeState={runtimeState} />}
      className="device-card relay-card"
    >
        {/* Preview Sekcia - Veľká ikona */}
        <div className="device-preview">
            <div className="device-large-icon">
              <DeviceIcon device={device} size={64} strokeWidth={1.4} />
            </div>
        </div>

        {/* Tlačidlá naspodku */}
        <div className="card-controls-footer">
          <ButtonGroup>
            <Button 
              variant="secondary" 
              onClick={() => handleCommand("OFF", "VYPNUTÉ")}
              icon={PowerOff}
              isLoading={isLoading}
              aria-label={`Vypnúť ${device.name}`}
            >
              Vypnúť
            </Button>
            <Button 
              variant="success" 
              onClick={() => handleCommand("ON", "ZAPNUTÉ")}
              icon={Power}
              isLoading={isLoading}
              aria-label={`Zapnúť ${device.name}`}
            >
              Zapnúť
            </Button>
          </ButtonGroup>
        </div>
    </Card>
  );
}
