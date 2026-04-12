import { useState, useEffect } from 'react';
import { useSocket } from '../../context/useSocket';
import { useScenes } from '../../hooks/useScenes';
import { useDevices } from '../../hooks/useDevices';
import { useDeviceRuntimeState } from '../../hooks/useDeviceRuntimeState';
import SceneVisualizer from '../Scenes/SceneVisualizer';
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import { Activity, Play, Zap, Power, Cpu, RefreshCw } from 'lucide-react';
import '../../styles/views/live-view.css';

export default function LiveView({
    embedded = false,
    selectedScene: controlledSelectedScene = null,
    sceneData: controlledSceneData = null,
    showSceneSelector = true,
    onSceneDataLoaded,
}) {
    const { socket } = useSocket();
    const { scenes, loadSceneContent, playScene, fetchScenes } = useScenes();
    const { devices } = useDevices();
    const { getStateForDevice, getDisplayStateForDevice } = useDeviceRuntimeState();

    const [internalSelectedScene, setInternalSelectedScene] = useState(null);
    const [internalSceneData, setInternalSceneData] = useState(null);
    const [activeState, setActiveState] = useState(null);

    const selectedScene = controlledSelectedScene ?? internalSelectedScene;
    const sceneData = controlledSceneData ?? internalSceneData;

    useEffect(() => {
        if (showSceneSelector) {
            fetchScenes();
        }
    }, [showSceneSelector, fetchScenes]);

    useEffect(() => {
        if (!socket) return;

        const handleProgress = (data) => {
            if (data?.activeState) {
                setActiveState(data.activeState);
            }
        };

        socket.on('scene_progress', handleProgress);
        return () => socket.off('scene_progress', handleProgress);
    }, [socket]);

    const handleSelectScene = async (e) => {
        const filename = e.target.value;
        setInternalSelectedScene(filename);
        if (!filename) return;

        const content = await loadSceneContent(filename);
        setInternalSceneData(content);
        onSceneDataLoaded?.(filename, content);
        setActiveState(null);
    };

    const handlePlay = () => {
        if (!selectedScene) return;
        playScene(selectedScene);
        setActiveState(null);
    };

    const sceneLabel = selectedScene
        ? selectedScene.replace('.json', '')
        : 'Žiadna scéna';

    const liveControls = (
        <div className="live-header-controls">
            {showSceneSelector ? (
                <select
                    className="live-select"
                    onChange={handleSelectScene}
                    value={selectedScene || ''}
                >
                    <option value="" disabled>-- Vyber scénu --</option>
                    {scenes.map((scene) => (
                        <option key={scene.name} value={scene.name}>
                            {scene.name}
                        </option>
                    ))}
                </select>
            ) : (
                <div className="live-current-scene">
                    Aktuálna scéna: {sceneLabel}
                </div>
            )}

            <Button
                variant="primary"
                icon={Play}
                onClick={handlePlay}
                disabled={!selectedScene}
            >
                Spustiť na RPi
            </Button>
        </div>
    );

    const liveContent = (
        <>
            {embedded ? (
                <div className="live-view-inline-header">
                    <h2 className="live-view-inline-title">Live Testovanie</h2>
                    <p className="live-view-inline-subtitle">
                        Sledovanie priebehu scény a stavu zariadení
                    </p>
                    {liveControls}
                </div>
            ) : (
                <PageHeader
                    title="Live Testovanie"
                    icon={Activity}
                    subtitle="Sledovanie priebehu scény a stavu zariadení"
                >
                    {liveControls}
                </PageHeader>
            )}

            <div className="live-grid">
                <div className="visualizer-panel">
                    {sceneData ? (
                        <>
                            <div className="visualizer-overlay">
                                STAV: {activeState || 'READY'}
                            </div>
                            <SceneVisualizer
                                data={sceneData}
                                activeStateId={activeState}
                            />
                        </>
                    ) : (
                        <div className="empty-state">
                            <Activity size={48} opacity={0.2} />
                            <div>Vyberte scénu zo zoznamu</div>
                        </div>
                    )}
                </div>

                <div className="devices-panel">
                    <div className="devices-header">
                        <Zap size={18} className="text-primary" />
                        Live Status
                    </div>

                    <div className="devices-list">
                        {devices.length === 0 ? (
                            <div className="text-muted text-sm p-4 text-center">
                                Žiadne zariadenia v devices.json
                            </div>
                        ) : (
                            devices.map((device) => {
                                const confirmedState = getStateForDevice(device);
                                const stateLabel = getDisplayStateForDevice(device);
                                const isOn = confirmedState === 'ON';
                                const isRelay = device.type === 'relay';

                                return (
                                    <div
                                        key={device.id}
                                        className={`device-item ${isOn ? 'active' : ''}`}
                                    >
                                        <div className="device-info">
                                            <div className="device-icon">
                                                {isRelay
                                                    ? <Power size={18} />
                                                    : <Cpu size={18} />}
                                            </div>
                                            <div>
                                                <div className="device-name">
                                                    {device.name}
                                                </div>
                                                <div className="device-id">
                                                    {device.id}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="device-status">
                                            {stateLabel}
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </div>
            </div>
        </>
    );

    if (embedded) {
        return (
            <div className="live-view-container live-view-embedded">
                {liveContent}
            </div>
        );
    }

    return (
        <div className="view-container live-view-container">
            {liveContent}
        </div>
    );
}