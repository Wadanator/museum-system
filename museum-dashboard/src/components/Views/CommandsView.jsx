import { useState } from 'react';
import { Loader2, Zap, Settings2, RefreshCw, OctagonX, SlidersHorizontal, SquareSplitVertical } from 'lucide-react';
import toast from 'react-hot-toast';
import { useDevices } from '../../hooks/useDevices';
import { useDeviceRuntimeState } from '../../hooks/useDeviceRuntimeState';
import { api } from '../../services/api';
import { useConfirm } from '../../context/useConfirm';
import MotorCard from '../Devices/MotorCard';
import RelayCard from '../Devices/RelayCard';
import WindowCard from '../Devices/WindowCard';
import DevicesConfigModal from '../Devices/DevicesConfigModal';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import StateNotice from '../ui/StateNotice';
import '../../styles/views/commands-view.css';

export default function CommandsView() {
    const { motors, relays, windows, loading, error } = useDevices();
    const { deviceStates, getStateForDevice, getDisplayStateForDevice } = useDeviceRuntimeState();
    const [isDevicesEditorOpen, setIsDevicesEditorOpen] = useState(false);
    const [devicesConfig, setDevicesConfig] = useState({ relays: [], motors: [], windows: [] });
    const { confirm } = useConfirm();

    const hasDevices = motors.length > 0 || relays.length > 0 || windows.length > 0;

    const getRuntimeState = (device) => {
        const entry = deviceStates[device.topic] || null;
        const confirmedState = getStateForDevice(device);
        const displayState = getDisplayStateForDevice(device);
        const isPending = Boolean(
            entry?.desired_state
            && entry.desired_state !== entry.confirmed_state
            && !entry.stale
        );
        const isStale = Boolean(entry?.stale);

        return {
            topic: device.topic,
            entry,
            confirmedState,
            displayState,
            isPending,
            isStale,
        };
    };

    const handleRefresh = () => window.location.reload();

    const handleStopAll = async () => {
        const confirmed = await confirm({
            title: 'Zastaviť všetko?',
            message: 'Naozaj chcete okamžite zastaviť scénu a vypnúť všetky motory, relé a okná?',
            confirmText: 'Zastaviť všetko',
            cancelText: 'Zrušiť',
            type: 'danger',
        });
        if (!confirmed) return;

        const toastId = toast.loading('Zastavujem scénu a zariadenia...');

        try {
            await api.stopScene();
            toast.success('Scéna aj všetky zariadenia boli zastavené.', { id: toastId });
        } catch (e) {
            console.error("Stop All Error:", e);
            toast.error("Chyba pri hromadnom vypínaní.", { id: toastId });
        }
    };

    const handleOpenDevicesEditor = async () => {
        try {
            const config = await api.getDevices();
            setDevicesConfig(config || { relays: [], motors: [], windows: [] });
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
            message="Zoznam motorov, relé, okien a efektov sa načítava z konfigurácie."
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
                subtitle="Manuálna kontrola motorov, okien a efektov"
                icon={Zap}
            >
                <Button 
                    variant="toolbar-danger" 
                    icon={OctagonX} 
                    onClick={handleStopAll} 
                    disabled={!hasDevices}
                >
                    Zastaviť všetko
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
                                <MotorCard
                                    key={motor.id || idx}
                                    device={motor}
                                    runtimeState={getRuntimeState(motor)}
                                />
                            ))}
                        </div>
                    </section>
                )}

                {motors.length > 0 && windows.length > 0 && <div className="section-divider"></div>}

                {windows.length > 0 && (
                    <section className="device-section">
                        <div className="section-header">
                            <SquareSplitVertical size={20} className="section-icon" />
                            <h3>Okná</h3>
                            <span className="count-badge">{windows.length}</span>
                        </div>
                        <div className="devices-grid windows-grid">
                            {windows.map((windowDevice, idx) => (
                                <WindowCard
                                    key={windowDevice.id || idx}
                                    device={windowDevice}
                                    runtimeState={getRuntimeState(windowDevice)}
                                />
                            ))}
                        </div>
                    </section>
                )}

                {(motors.length > 0 || windows.length > 0) && relays.length > 0 && <div className="section-divider"></div>}

                {relays.length > 0 && (
                    <section className="device-section">
                        <div className="section-header">
                            <Zap size={20} className="section-icon" />
                            <h3>Osvetlenie & Efekty</h3>
                            <span className="count-badge">{relays.length}</span>
                        </div>
                        <div className="devices-grid relays-grid">
                            {relays.map((relay, idx) => (
                                <RelayCard
                                    key={relay.id || idx}
                                    device={relay}
                                    runtimeState={getRuntimeState(relay)}
                                />
                            ))}
                        </div>
                    </section>
                )}

                {!hasDevices && (
                    <StateNotice
                        icon={SlidersHorizontal}
                        title="Žiadne zariadenia"
                        message="V konfigurácii zatiaľ nie sú pridané motory, okná, relé ani efekty."
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
