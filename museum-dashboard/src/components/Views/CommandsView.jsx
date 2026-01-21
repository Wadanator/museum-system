import { Loader2, Zap, Settings2, RefreshCw, OctagonX } from 'lucide-react';
import toast from 'react-hot-toast';
import { useDevices } from '../../hooks/useDevices';
import { api } from '../../services/api';
import MotorCard from '../Devices/MotorCard';
import RelayCard from '../Devices/RelayCard';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import '../../styles/views/commands-view.css';

export default function CommandsView() {
    const { motors, relays, loading, error } = useDevices();

    const handleRefresh = () => window.location.reload();

    const handleStopAll = async () => {
        const confirmed = window.confirm("Naozaj chcete okamžite vypnúť všetky motory a relé?");
        if (!confirmed) return;

        const toastId = toast.loading("Vypínam všetky zariadenia...");

        try {
            const promises = [
                ...motors.map(m => api.sendMqtt(m.topic, 0)),
                ...relays.map(r => api.sendMqtt(r.topic, 0))
            ];

            await Promise.all(promises);
            toast.success("Všetky zariadenia boli vypnuté.", { id: toastId });
        } catch (e) {
            console.error("Stop All Error:", e);
            toast.error("Chyba pri hromadnom vypínaní.", { id: toastId });
        }
    };

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
            <PageHeader 
                title="Ovládanie Zariadení" 
                subtitle="Manuálna kontrola motorov a efektov"
                icon={Zap}
            >
                {/* Opravené: Použitie CSS triedy namiesto inline štýlu */}
                <div className="page-header-actions">
                    <Button 
                        variant="danger" 
                        icon={OctagonX} 
                        onClick={handleStopAll} 
                        disabled={motors.length === 0 && relays.length === 0}
                    >
                        VYPNÚŤ VŠETKO
                    </Button>

                    <Button variant="secondary" icon={RefreshCw} onClick={handleRefresh} size="small">
                        Obnoviť
                    </Button>
                </div>
            </PageHeader>

            <div className="devices-content">
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

                {motors.length > 0 && relays.length > 0 && <div className="section-divider"></div>}

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

                {motors.length === 0 && relays.length === 0 && (
                    <div className="empty-state">
                        Nenašli sa žiadne zariadenia v konfigurácii.
                    </div>
                )}
            </div>
        </div>
    );
}