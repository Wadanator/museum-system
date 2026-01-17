import toast from 'react-hot-toast';
import { Rewind, FastForward, Square } from 'lucide-react';
import { api } from '../../services/api';
import Card from '../ui/Card';
import Button from '../ui/Button';

export default function MotorCard({ device }) {
  const speed = device.speed || 100;

  const sendCmd = async (cmd, label) => {
      let payload;
      if (cmd === 'LEFT') payload = `ON:${speed}:L`;
      if (cmd === 'RIGHT') payload = `ON:${speed}:R`;
      if (cmd === 'STOP') payload = `OFF`;

      try {
        await api.sendMqtt(device.topic, payload);
        toast.success(`${device.name}: ${label}`);
      } catch (e) {
        toast.error("Chyba motora");
      }
  };

  return (
    <Card 
        title={device.name} 
        actions={<span className="badge">{speed}% SPD</span>}
    >
        <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
            <Button 
                variant="secondary" 
                onClick={() => sendCmd('LEFT', 'Vzad')} 
                style={{ flex: 1 }}
                icon={Rewind}
            >
                Vzad
            </Button>
            
            <Button 
                variant="danger" 
                onClick={() => sendCmd('STOP', 'Stop')}
                icon={Square}
            >
                STOP
            </Button>
            
            <Button 
                variant="secondary" 
                onClick={() => sendCmd('RIGHT', 'Vpred')} 
                style={{ flex: 1 }}
                icon={FastForward}
            >
                Vpred
            </Button>
        </div>
    </Card>
  );
}