import { Rewind, FastForward, Square, Gauge } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import StatusBadge from '../ui/StatusBadge';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function MotorCard({ device }) {
  const speed = device.speed || 100;
  const { sendCommand } = useDeviceControl(device.topic, device.name);

  const handleAction = (direction, label) => {
      let payload = `OFF`;
      if (direction === 'LEFT') payload = `ON:${speed}:L`;
      else if (direction === 'RIGHT') payload = `ON:${speed}:R`;

      sendCommand(payload, label);
  };

  return (
    <Card 
        title={device.name} 
        icon={Gauge} 
        actions={<StatusBadge status="info" label={`${speed}%`} />}
        className="device-card motor-card"
    >
        <div className="card-description">
            Ovládanie smeru a rýchlosti motorickej jednotky.
        </div>

        {/* Preview pre motor - Tu môžeme dať ikonu alebo nechať prázdne pre space */}
        <div className="device-preview" style={{ opacity: 0.1 }}>
             <Gauge size={64} color="var(--text-primary)" />
        </div>

        <div className="card-controls-footer">
            <ButtonGroup>
                <Button 
                    variant="secondary" 
                    onClick={() => handleAction('LEFT', 'Vzad')} 
                    icon={Rewind}
                    style={{ flex: 1 }}
                >
                    Vzad
                </Button>
                
                <Button 
                    variant="danger" 
                    onClick={() => handleAction('STOP', 'Stop')}
                    icon={Square}
                >
                    STOP
                </Button>
                
                <Button 
                    variant="secondary" 
                    onClick={() => handleAction('RIGHT', 'Vpred')} 
                    icon={FastForward}
                    style={{ flex: 1 }}
                >
                    Vpred
                </Button>
            </ButtonGroup>
        </div>
    </Card>
  );
}