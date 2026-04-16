import { useState } from 'react';
import { Loader2, Zap, Settings2, RefreshCw, OctagonX, FileCode2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useDevices } from '../../hooks/useDevices';
import { api } from '../../services/api';
import MotorCard from '../Devices/MotorCard';
import RelayCard from '../Devices/RelayCard';
import DevicesConfigModal from '../Devices/DevicesConfigModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import '../../styles/views/commands-view.css';

export default function CommandsView() {
    const { motors, relays, loading, error } = useDevices();
    const [isDevicesEditorOpen, setIsDevicesEditorOpen] = useState(false);
    const [devicesConfig, setDevicesConfig] = useState({ relays: [], motors: [] });

    const handleRefresh = () => window.location.reload();

    const handleStopAll = async () => {
        const confirmed = window.confirm("Naozaj chcete okamžite vypnúť všetky motory a relé?");
        if (!confirmed) return;

        const toastId = toast.loading("Vypínam všetky zariadenia...");

        try {
            const status = await api.getStatus(); 
            const roomId = status.room_id;

            if (!roomId) {
                throw new Error("Nepodarilo sa zistiť Room ID zo servera.");
            }

            await api.sendMqtt(`${roomId}/STOP`, 'STOP');

            toast.success(`Všetky zariadenia v ${roomId} boli vypnuté.`, { id: toastId });
        } catch (e) {
            console.error("Stop All Error:", e);
            toast.error("Chyba pri hromadnom vypínaní.", { id: toastId });
        }
    };

    const handleOpenDevicesEditor = async () => {
        try {
            const config = await api.getDevices();
            setDevicesConfig(config || { relays: [], motors: [] });
            setIsDevicesEditorOpen(true);
        } catch (e) {
            console.error('Load devices config error:', e);
            toast.error('Nepodarilo sa načítať devices konfiguráciu.');
        }
    };

    const handleSaveDevicesConfig = async (updatedConfig) => {
        try {
            const result = await api.saveDevices(updatedConfig);
            if (result?.success) {
                return { success: true };
            }
            return { success: false, error: result?.error || 'Save failed' };
        } catch (e) {
            console.error('Save devices config error:', e);
            return { success: false, error: e.message || 'Save failed' };
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

                <Button variant="secondary" icon={FileCode2} onClick={handleOpenDevicesEditor} size="small">
                    Upraviť devices.json
                </Button>
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

            <DevicesConfigModal
                isOpen={isDevicesEditorOpen}
                onClose={() => setIsDevicesEditorOpen(false)}
                initialContent={devicesConfig}
                onSave={handleSaveDevicesConfig}
            />
        </div>
    );
}