import { useState } from 'react'; // Pridaný useState
import { Rewind, FastForward, Square } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import StatusBadge from '../ui/StatusBadge';
import DeviceIcon, { getDeviceIconComponent } from './DeviceIcon';
import DeviceRuntimeIndicator from './DeviceRuntimeIndicator';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function MotorCard({ device, runtimeState }) {
  const speed = device.speed || 100;
  const HeaderIcon = getDeviceIconComponent(device);
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [loading, setLoading] = useState(false);

  const handleAction = async (direction, label) => { 
      if (loading) return;

      setLoading(true);
      
      let payload = `OFF`;
      if (direction === 'LEFT') payload = `ON:${speed}:L`;
      else if (direction === 'RIGHT') payload = `ON:${speed}:R`;

      try {
        await sendCommand(payload, label);
      } finally {
        setLoading(false);
      }
  };

  return (
    <Card 
        title={device.name} 
        icon={HeaderIcon} 
        actions={(
          <div className="device-card-actions">
            <StatusBadge status="info" label={`${speed}%`} />
            <DeviceRuntimeIndicator runtimeState={runtimeState} />
          </div>
        )}
        className="device-card motor-card"
    >
        <div className="card-description">
            Ovládanie smeru a rýchlosti motorickej jednotky.
        </div>

           <div className="device-preview device-preview--faded">
             <DeviceIcon device={device} size={64} color="var(--text-primary)" />
        </div>

        <div className="card-controls-footer">
            <ButtonGroup>
                <Button 
                    variant="secondary" 
                    onClick={() => handleAction('LEFT', 'Vzad')} 
                    icon={Rewind}
                    isLoading={loading}
                >
                    Vzad
                </Button>
                
                <Button 
                    variant="danger" 
                    onClick={() => handleAction('STOP', 'Stop')}
                    icon={Square}
                    isLoading={loading}
                >
                    STOP
                </Button>
                
                <Button 
                    variant="secondary" 
                    onClick={() => handleAction('RIGHT', 'Vpred')} 
                    icon={FastForward}
                    isLoading={loading}
                >
                    Vpred
                </Button>
            </ButtonGroup>
        </div>
    </Card>
  );
}
