import { Rewind, FastForward, Square, Gauge } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
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

  // Hlavička karty s rýchlosťou (Opravený Badge)
  const headerAction = (
      <div className="status-badge info">
          <Gauge size={14} />
          <span>{speed}%</span>
      </div>
  );

  return (
    <Card 
        title={device.name} 
        actions={headerAction}
        className="device-card motor-card"
    >
        <div className="card-description">
            Ovládanie smeru a rýchlosti motorickej jednotky.
        </div>

        <div className="motor-controls">
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