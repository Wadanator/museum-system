import { Server, Power, RefreshCw, HardDrive } from 'lucide-react';
import { useSystemActions } from '../../hooks/useSystemActions';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';

export default function SystemView() {
    const { restartService, rebootSystem, shutdownSystem } = useSystemActions();

    return (
        <div className="view-container">
            <h2 className="view-title">Systémové nastavenia</h2>
            
            <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
                
                {/* Karta: Správa Aplikácie */}
                <Card title="Aplikácia Múzeum" icon={Server}>
                    <p style={{ marginBottom: '15px', color: '#666' }}>
                        Ovládanie hlavnej služby Python backendu. Použite pri zaseknutí logiky.
                    </p>
                    <Button 
                        onClick={restartService} 
                        variant="secondary" 
                        icon={RefreshCw}
                        style={{ width: '100%' }}
                    >
                        Reštartovať Backend službu
                    </Button>
                </Card>

                {/* Karta: Správa Hardvéru */}
                <Card title="Napájanie Zariadenia" icon={HardDrive}>
                    <p style={{ marginBottom: '15px', color: '#666' }}>
                        Ovládanie celého počítača (Raspberry Pi).
                    </p>
                    <ButtonGroup>
                        <Button 
                            onClick={rebootSystem} 
                            variant="secondary" 
                            icon={RefreshCw}
                            style={{ flex: 1 }}
                        >
                            Reštartovať RPi
                        </Button>
                        <Button 
                            onClick={shutdownSystem} 
                            variant="danger" 
                            icon={Power}
                            style={{ flex: 1 }}
                        >
                            Vypnúť
                        </Button>
                    </ButtonGroup>
                </Card>

            </div>
        </div>
    );
}