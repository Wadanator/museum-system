import { Zap, Power, PowerOff, Lightbulb } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import { useDeviceControl } from '../../hooks/useDeviceControl';

export default function RelayCard({ device }) {
  const { sendCommand } = useDeviceControl(device.topic, device.name);

  // Rozhodneme, akú ikonu použiť v hlavičke (ak je to svetlo -> žiarovka, inak blesk)
  // Toto je bezpečné, žiadne regexy
  const HeaderIcon = device.id.includes('light') ? Lightbulb : Zap;

  // Custom ikona z JSONu (napr. emoji)
  const customIcon = device.icon || null;

  return (
    <Card 
        title={device.name} 
        icon={HeaderIcon} 
        className="device-card relay-card"
    >
        {/* Ak máme custom ikonu (emoji), zobrazíme ju veľkú v strede */}
        {customIcon && (
            <div className="device-emoji-preview">
                {customIcon}
            </div>
        )}
        
        <div className="relay-controls" style={{ marginTop: 'auto' }}>
            <ButtonGroup>
                <Button 
                    variant="secondary" 
                    onClick={() => sendCommand("OFF", "VYPNUTÉ")}
                    icon={PowerOff}
                    style={{ flex: 1 }}
                >
                    Vypnúť
                </Button>
                <Button 
                    variant="success" 
                    onClick={() => sendCommand("ON", "ZAPNUTÉ")}
                    icon={Power}
                    style={{ flex: 1 }}
                >
                    Zapnúť
                </Button>
            </ButtonGroup>
        </div>
    </Card>
  );
}