import { useState, useCallback } from 'react';
import { Zap, Power, PowerOff, Lightbulb } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function RelayCard({ device }) {
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [isLoading, setIsLoading] = useState(false);

  // Ikona v hlavičke karty
  const HeaderIcon = device.id?.includes('light') ? Lightbulb : Zap;
  
  // Veľká ikona v strede (ak nie je definovaná v configu, dáme default)
  const customIcon = device.icon || (device.id?.includes('light') ? '💡' : '⚡');

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
      className="device-card relay-card"
    >
        {/* Preview Sekcia - Veľká ikona */}
        <div className="device-preview">
            <div className="emoji-large">{customIcon}</div>
        </div>

        {/* Tlačidlá naspodku */}
        <div className="card-controls-footer">
          <ButtonGroup>
            <Button 
              variant="secondary" 
              onClick={() => handleCommand("OFF", "VYPNUTÉ")}
              icon={PowerOff}
              isLoading={isLoading}
              style={{ flex: 1 }}
              aria-label={`Vypnúť ${device.name}`}
            >
              Vypnúť
            </Button>
            <Button 
              variant="success" 
              onClick={() => handleCommand("ON", "ZAPNUTÉ")}
              icon={Power}
              isLoading={isLoading}
              style={{ flex: 1 }}
              aria-label={`Zapnúť ${device.name}`}
            >
              Zapnúť
            </Button>
          </ButtonGroup>
        </div>
    </Card>
  );
}