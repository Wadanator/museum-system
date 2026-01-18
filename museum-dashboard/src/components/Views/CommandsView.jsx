import { Loader2, Zap, Settings2, RefreshCw } from 'lucide-react';
import { useDevices } from '../../hooks/useDevices';
import MotorCard from '../Devices/MotorCard';
import RelayCard from '../Devices/RelayCard';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import '../../styles/views/commands-view.css';

export default function CommandsView() {
    const { motors, relays, loading, error } = useDevices();

    const handleRefresh = () => window.location.reload();

    if (loading) return (
        <div className="loading-state">
            <Loader2 className="animate-spin" size={40} />
            <p>Načítavam zariadenia...</p>
        </div>
    );

    if (error) return (
        <div className="error-state">
            <p>Chyba načítania: {error}</p>
            <Button onClick={handleRefresh} variant="secondary">Skúsiť znova</Button>
        </div>
    );

    return (
        <div className="view-container commands-view">
            {/* Nový Header */}
            <PageHeader 
                title="Ovládanie Zariadení" 
                subtitle="Manuálna kontrola motorov a efektov"
                icon={Zap}
            >
                <Button variant="secondary" icon={RefreshCw} onClick={handleRefresh} size="small">
                    Obnoviť
                </Button>
            </PageHeader>

            <div className="devices-content">
                {/* 1. SEKCIA: MOTORY */}
                {motors.length > 0 && (
                    <section className="device-section">
                        <div className="section-header">
                            <Settings2 size={20} className="section-icon" />
                            <h3>Motorizácia</h3>
                            <span className="count-badge">{motors.length}</span>
                        </div>
                        <div className="devices-grid motors-grid">
                            {motors.map((motor, idx) => (
                                <MotorCard key={motor.id || idx} device={motor} />
                            ))}
                        </div>
                    </section>
                )}

                {/* Čiara medzi sekciami */}
                {motors.length > 0 && relays.length > 0 && <div className="section-divider"></div>}

                {/* 2. SEKCIA: SVETLÁ A RELÉ */}
                {relays.length > 0 && (
                    <section className="device-section">
                        <div className="section-header">
                            <Zap size={20} className="section-icon" />
                            <h3>Osvetlenie & Efekty</h3>
                            <span className="count-badge">{relays.length}</span>
                        </div>
                        <div className="devices-grid relays-grid">
                            {relays.map((relay, idx) => (
                                <RelayCard key={relay.id || idx} device={relay} />
                            ))}
                        </div>
                    </section>
                )}

                {/* Empty State */}
                {motors.length === 0 && relays.length === 0 && (
                    <div className="empty-state">
                        Nenašli sa žiadne zariadenia v konfigurácii.
                    </div>
                )}
            </div>
        </div>
    );
}