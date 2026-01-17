import toast from 'react-hot-toast';
import { Play, Square } from 'lucide-react';
import { api } from '../../services/api';

export default function MotorCard({ device }) {
  const speed = device.speed || 100;

  const sendCmd = async (cmd, label) => {
      let payload;
      // Formát príkazu podľa tvojho backendu
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
    <div className="device-card">
        {/* Hlavička motora */}
        <div className="motor-header">
            <span className="motor-title">{device.name}</span>
            <span className="motor-meta">{speed}% SPD</span>
        </div>

        {/* Ovládacie tlačidlá */}
        <div className="motor-controls">
            {/* Tlačidlo VZAD (Otočená Play ikona) */}
            <button 
                className="btn-motor btn-motor-nav" 
                onClick={() => sendCmd('LEFT', 'Vzad')}
            >
                <Play 
                    size={18} 
                    style={{ transform: 'rotate(180deg)' }} 
                    fill="currentColor" 
                /> 
                Vzad
            </button>
            
            {/* Tlačidlo STOP */}
            <button 
                className="btn-motor btn-stop" 
                onClick={() => sendCmd('STOP', 'Stop')}
            >
                <Square size={16} fill="currentColor" /> 
                STOP
            </button>
            
            {/* Tlačidlo VPRED */}
            <button 
                className="btn-motor btn-motor-nav" 
                onClick={() => sendCmd('RIGHT', 'Vpred')}
            >
                Vpred 
                <Play size={18} fill="currentColor" />
            </button>
        </div>
    </div>
  );
}