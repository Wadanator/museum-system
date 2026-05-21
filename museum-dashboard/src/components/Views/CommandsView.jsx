import { useState } from 'react';
import { Loader2, Zap, Settings2, RefreshCw, OctagonX, SlidersHorizontal } from 'lucide-react';
import toast from 'react-hot-toast';
import { useDevices } from '../../hooks/useDevices';
import { api } from '../../services/api';
import { useConfirm } from '../../context/useConfirm';
import MotorCard from '../Devices/MotorCard';
import RelayCard from '../Devices/RelayCard';
import DevicesConfigModal from '../Devices/DevicesConfigModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import StateNotice from '../ui/StateNotice';
import '../../styles/views/commands-view.css';

export default function CommandsView() {
    const { motors, relays, loading, error } = useDevices();
    const [isDevicesEditorOpen, setIsDevicesEditorOpen] = useState(false);
    const [devicesConfig, setDevicesConfig] = useState({ relays: [], motors: [] });
    const { confirm } = useConfirm();

    const handleRefresh = () => window.location.reload();

    const handleStopAll = async () => {
        const confirmed = await confirm({
            title: 'Vypnúť všetky zariadenia?',
            message: 'Naozaj chcete okamžite vypnúť všetky motory a relé?',
            confirmText: 'Vypnúť všetko',
            cancelText: 'Zrušiť',
            type: 'danger',
        });
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
        <StateNotice
            icon={Loader2}
            title="Načítavam zariadenia"
            message="Zoznam motorov, relé a efektov sa načítava z konfigurácie."
            isLoading
        />
    );

    if (error) return (
        <StateNotice
            icon={OctagonX}
            title="Zariadenia sa nepodarilo načítať"
            message={error}
            tone="danger"
        >
            <Button onClick={handleRefresh} variant="toolbar">Skúsiť znova</Button>
        </StateNotice>
    );

    return (
        <div className="view-container commands-view">
            <PageHeader 
                title="Ovládanie zariadení" 
                subtitle="Manuálna kontrola motorov a efektov"
                icon={Zap}
            >
                <Button 
                    variant="toolbar-danger" 
                    icon={OctagonX} 
                    onClick={handleStopAll} 
                    disabled={motors.length === 0 && relays.length === 0}
                >
                    Vypnúť všetko
                </Button>

                <Button variant="toolbar" icon={RefreshCw} onClick={handleRefresh} size="small">
                    Obnoviť
                </Button>

                <Button
                    variant="toolbar"
                    icon={SlidersHorizontal}
                    onClick={handleOpenDevicesEditor}
                    size="small"
                    title="Upraviť devices.json"
                >
                    Konfigurácia zariadení
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
                    <StateNotice
                        icon={SlidersHorizontal}
                        title="Žiadne zariadenia"
                        message="V konfigurácii zatiaľ nie sú pridané motory, relé ani efekty."
                    >
                        <Button variant="toolbar-primary" icon={SlidersHorizontal} onClick={handleOpenDevicesEditor}>
                            Otvoriť konfiguráciu
                        </Button>
                    </StateNotice>
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
