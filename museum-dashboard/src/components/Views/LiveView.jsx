import { useState, useEffect } from 'react';
import { useScenes } from '../../hooks/useScenes';
import { useDevices } from '../../hooks/useDevices';
import { useDeviceRuntimeState } from '../../hooks/useDeviceRuntimeState';
import { useSceneProgress } from '../../hooks/useSceneProgress';
import { useRuntime } from '../../context/useRuntime';
import SceneVisualizer from '../Scenes/SceneVisualizer';
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import StateNotice from '../ui/StateNotice';
import RuntimeStatusBar from '../Runtime/RuntimeStatusBar';
import { Activity, Play, Zap, Power, Cpu, RefreshCw } from 'lucide-react';
import '../../styles/views/live-view.css';

export default function LiveView({
    embedded = false,
    selectedScene: controlledSelectedScene = null,
    sceneData: controlledSceneData = null,
    showSceneSelector = true,
    onSceneDataLoaded,
}) {
    const { scenes, loadSceneContent, playScene, fetchScenes } = useScenes();
    const { devices } = useDevices();
    const { deviceStates, getStateForDevice, getDisplayStateForDevice } = useDeviceRuntimeState();
    const { activeState, resetActiveState } = useSceneProgress();
    const { sceneRunning, currentSceneName, runtimeSummary } = useRuntime();

    const [internalSelectedScene, setInternalSelectedScene] = useState(null);
    const [internalSceneData, setInternalSceneData] = useState(null);

    const runtimeSceneName = sceneRunning ? currentSceneName : null;
    const selectedScene = controlledSelectedScene ?? runtimeSceneName ?? internalSelectedScene;
    const sceneData = controlledSceneData ?? internalSceneData;

    useEffect(() => {
        if (showSceneSelector) {
            fetchScenes();
        }
    }, [showSceneSelector, fetchScenes]);

    useEffect(() => {
        if (!runtimeSceneName || controlledSceneData) return;
        if (runtimeSceneName === internalSelectedScene && internalSceneData) return;

        let cancelled = false;
        loadSceneContent(runtimeSceneName)
            .then((content) => {
                if (cancelled) return;
                setInternalSelectedScene(runtimeSceneName);
                setInternalSceneData(content);
                onSceneDataLoaded?.(runtimeSceneName, content);
            })
            .catch(() => {
                if (cancelled) return;
                setInternalSelectedScene(runtimeSceneName);
                setInternalSceneData(null);
            });

        return () => {
            cancelled = true;
        };
    }, [
        runtimeSceneName,
        controlledSceneData,
        internalSelectedScene,
        internalSceneData,
        loadSceneContent,
        onSceneDataLoaded,
    ]);

    const handleSelectScene = async (e) => {
        const filename = e.target.value;
        setInternalSelectedScene(filename);
        if (!filename) return;

        const content = await loadSceneContent(filename);
        setInternalSceneData(content);
        onSceneDataLoaded?.(filename, content);
        resetActiveState();
    };

    const handlePlay = () => {
        if (!selectedScene) return;
        playScene(selectedScene);
        resetActiveState();
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
                <>
                    <PageHeader
                    title="Live Testovanie"
                    icon={Activity}
                    subtitle="Sledovanie priebehu scény a stavu zariadení"
                    >
                        {liveControls}
                    </PageHeader>
                    <RuntimeStatusBar />
                </>
            )}

            <div className="live-grid">
                <div className="visualizer-panel">
                    {sceneData ? (
                        <>
                            <div className="visualizer-overlay">
                                STAV: {activeState === 'END' ? 'KONIEC' : (activeState || 'READY')}
                            </div>
                            <SceneVisualizer
                                data={sceneData}
                                activeStateId={activeState}
                            />
                        </>
                    ) : (
                        <StateNotice
                            icon={Activity}
                            title="Vyberte scénu"
                            message="Po výbere sa zobrazí priebeh scény a aktuálny stav zariadení."
                        />
                    )}
                </div>

                <div className="devices-panel">
                    <div className="devices-header">
                        <Zap size={18} className="text-primary" />
                        Live Status
                        <span className="devices-header-summary">
                            ON {runtimeSummary.on} / UNKNOWN {runtimeSummary.unknown}
                        </span>
                    </div>

                    <div className="devices-list">
                        {devices.length === 0 ? (
                            <StateNotice
                                icon={Zap}
                                title="Žiadne zariadenia"
                                message="V konfigurácii zatiaľ nie sú zariadenia pre live náhľad."
                                compact
                            />
                        ) : (
                            devices.map((device) => {
                                const entry = deviceStates[device.topic];
                                const confirmedState = getStateForDevice(device);
                                const stateLabel = getDisplayStateForDevice(device);
                                const isOn = confirmedState === 'ON';
                                const isRelay = device.type === 'relay';
                                const isPending = entry?.desired_state
                                    && entry.desired_state !== entry.confirmed_state
                                    && !entry.stale;
                                const isStale = Boolean(entry?.stale);

                                return (
                                    <div
                                        key={device.id}
                                        className={`device-item ${isOn ? 'active' : ''} ${isPending ? 'pending' : ''} ${isStale ? 'stale' : ''}`}
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
                                                    {isPending ? ' / PENDING' : ''}
                                                    {isStale ? ' / STALE' : ''}
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
