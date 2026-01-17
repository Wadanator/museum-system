import toast from 'react-hot-toast';
import { Zap, Power, PowerOff } from 'lucide-react';
import { api } from '../../services/api';
import Card from '../ui/Card';
import Button from '../ui/Button';

export default function RelayCard({ device }) {
  const sendCommand = async (cmd) => {
    try {
        await api.sendMqtt(device.topic, cmd);
        
        const label = cmd === 'ON' ? 'ZAPNUTÉ' : 'VYPNUTÉ';
        toast.success(`${device.name}: ${label}`, {
            icon: cmd === 'ON' ? '🟢' : '⚫',
            duration: 2000
        });

    } catch (e) {
        toast.error("Chyba komunikácie");
    }
  };

  return (
    <Card 
        title={device.name} 
        icon={device.icon ? Zap : undefined} // Tu by sa dala pridať logika pre dynamickú ikonu
        className="device-card"
    >
        <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '10px', 
            marginTop: '10px' 
        }}>
            <Button 
                variant="secondary" 
                onClick={() => sendCommand("OFF")}
                icon={PowerOff}
            >
                Vypnúť
            </Button>
            <Button 
                variant="success" 
                onClick={() => sendCommand("ON")}
                icon={Power}
            >
                Zapnúť
            </Button>
        </div>
    </Card>
  );
}