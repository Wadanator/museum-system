import { useState, useCallback } from 'react';
import { Zap, Power, PowerOff, Lightbulb } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function RelayCard({ device }) {
  const { sendCommand } = useDeviceControl(device.topic, device.name);
  const [isLoading, setIsLoading] = useState(false);

  // Determine which icon to use in the header
  const HeaderIcon = device.id?.includes('light') ? Lightbulb : Zap;
  const customIcon = device.icon || null;

  // Handle command with loading state
  const handleCommand = useCallback(async (command, displayText) => {
    setIsLoading(true);
    try {
      await sendCommand(command, displayText);
    } finally {
      setIsLoading(false);
    }
  }, [sendCommand]);

  const handleTurnOff = useCallback(() => {
    handleCommand("OFF", "VYPNUTÉ");
  }, [handleCommand]);

  const handleTurnOn = useCallback(() => {
    handleCommand("ON", "ZAPNUTÉ");
  }, [handleCommand]);

  return (
    <Card 
      title={device.name} 
      icon={HeaderIcon} 
      className="device-card relay-card"
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        
        {/* Custom emoji icon display */}
        {customIcon && (
          <div className="device-emoji-preview">
            {customIcon}
          </div>
        )}
        
        {/* Flexible spacer */}
        <div style={{ flex: 1 }} />

        {/* Control buttons at the bottom */}
        <div className="relay-controls">
          <ButtonGroup>
            <Button 
              variant="secondary" 
              onClick={handleTurnOff}
              icon={PowerOff}
              isLoading={isLoading}
              style={{ flex: 1 }}
              aria-label={`Vypnúť ${device.name}`}
            >
              Vypnúť
            </Button>
            <Button 
              variant="success" 
              onClick={handleTurnOn}
              icon={Power}
              isLoading={isLoading}
              style={{ flex: 1 }}
              aria-label={`Zapnúť ${device.name}`}
            >
              Zapnúť
            </Button>
          </ButtonGroup>
        </div>
      </div>
    </Card>
  );
}