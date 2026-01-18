import { Server, Power, RefreshCw, HardDrive, Settings } from 'lucide-react';
import { useSystemActions } from '../../hooks/useSystemActions';
import Card from '../ui/Card';
import Button from '../ui/Button';
import ButtonGroup from '../ui/ButtonGroup';
import PageHeader from '../ui/PageHeader';
import '../../styles/views/system-view.css'; // Import nového CSS

export default function SystemView() {
    const { restartService, rebootSystem, shutdownSystem } = useSystemActions();

    return (
        <div className="view-container system-view">
            <PageHeader 
                title="Systémové nastavenia" 
                subtitle="Správa servera a hardvéru"
                icon={Settings}
            />
            
            <div className="system-grid">
                
                {/* Karta: Správa Aplikácie */}
                <Card 
                    title="Aplikácia Múzeum" 
                    icon={Server}
                    className="system-card"
                >
                    <p className="system-card-description">
                        Ovládanie hlavnej služby Python backendu. Použite túto možnosť, ak aplikácia nereaguje, ale systém beží.
                    </p>
                    
                    <div className="system-card-actions">
                        <Button 
                            onClick={restartService} 
                            variant="secondary" 
                            icon={RefreshCw}
                            className="btn-full-width"
                        >
                            Reštartovať Backend službu
                        </Button>
                    </div>
                </Card>

                {/* Karta: Správa Hardvéru */}
                <Card 
                    title="Napájanie Zariadenia" 
                    icon={HardDrive}
                    className="system-card"
                >
                    <p className="system-card-description">
                        Fyzické ovládanie počítača (Raspberry Pi). Reštart trvá cca 2 minúty.
                    </p>
                    
                    <div className="system-card-actions">
                        <ButtonGroup>
                            <Button 
                                onClick={rebootSystem} 
                                variant="secondary" 
                                icon={RefreshCw}
                                style={{ flex: 1 }} // Flex pre ButtonGroup je OK (layout)
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
                    </div>
                </Card>

            </div>
        </div>
    );
}