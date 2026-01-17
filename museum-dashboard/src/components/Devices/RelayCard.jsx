import toast from 'react-hot-toast';
import { Zap } from 'lucide-react';
import { api } from '../../services/api';

export default function RelayCard({ device }) {
  // Funkcia na odoslanie príkazu
  const sendCommand = async (cmd) => {
    try {
        await api.sendMqtt(device.topic, cmd);
        // Toast notifikácia
        const label = cmd === 'ON' ? 'ZAPNUTÉ' : 'VYPNUTÉ';
        toast.success(`${device.name}: ${label}`, {
            icon: cmd === 'ON' ? '🟢' : '🔴',
        });
    } catch (e) {
        toast.error("Chyba komunikácie");
    }
  };

  // Zistíme stav (predpokladáme, že device.state je boolean alebo 'ON'/'OFF')
  // Ak nemáš live stav v objekte device, trieda 'active' sa nebude meniť, ale tlačidlá budú fungovať.
  const isOn = device.state === true || device.state === 'ON';

  return (
    <div className="device-card">
        {/* Hlavička s veľkou ikonou */}
        <div className="relay-header">
            <Zap className="relay-icon" style={{ color: isOn ? '#10b981' : '#4b5563' }} />
            <span className="relay-name">{device.name}</span>
        </div>

        {/* Prepínač (Segmented Control) */}
        <div className="btn-group-dual">
            <button 
                className={`btn-dual off ${!isOn ? 'active' : ''}`}
                onClick={() => sendCommand("OFF")}
            >
                Vypnúť
            </button>
            <button 
                className={`btn-dual on ${isOn ? 'active' : ''}`}
                onClick={() => sendCommand("ON")}
            >
                Zapnúť
            </button>
        </div>
    </div>
  );
}