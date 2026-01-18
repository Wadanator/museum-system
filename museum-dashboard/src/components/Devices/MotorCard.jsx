import { Rewind, FastForward, Square, Gauge } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import StatusBadge from '../ui/StatusBadge';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function MotorCard({ device }) {
  const speed = device.speed || 100;
  const { sendCommand } = useDeviceControl(device.topic, device.name);

  // Funkcia na odoslanie príkazu
  const handleAction = (direction, label) => {
      let payload;
      if (direction === 'LEFT') payload = `ON:${speed}:L`;
      else if (direction === 'RIGHT') payload = `ON:${speed}:R`;
      else payload = `OFF`;

      sendCommand(payload, label);
  };

  // Hlavička karty s rýchlosťou
  const headerAction = (
      <StatusBadge 
          status="info" 
          label={`${speed}%`} 
      />
  );

  return (
    <Card 
        title={device.name} 
        icon={Gauge} 
        actions={headerAction}
        className="device-card motor-card"
    >
        <div className="card-description">
            Ovládanie smeru a rýchlosti motorickej jednotky.
        </div>

        <div className="motor-controls" style={{ marginTop: 'auto' }}>
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