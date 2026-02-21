import { useState, useEffect, useRef } from 'react';
import { useSocket } from '../../context/SocketContext';
import { useScenes } from '../../hooks/useScenes';
import { useDevices } from '../../hooks/useDevices';
import SceneVisualizer from '../Scenes/SceneVisualizer';
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import { Activity, Play, Zap, Power, Cpu, RefreshCw } from 'lucide-react';
import '../../styles/views/live-view.css';

export default function LiveView({ embedded = false }) {
    const { socket } = useSocket();
    const { scenes, loadSceneContent, playScene, fetchScenes } = useScenes();
    const { devices } = useDevices();

    const [selectedScene, setSelectedScene] = useState(null);
    const [sceneData, setSceneData] = useState(null);
    const [activeState, setActiveState] = useState(null);
    const [simulatedDeviceStatus, setSimulatedDeviceStatus] = useState({});

    const timersRef = useRef([]);

    const applyActions = (actions) => {
        setSimulatedDeviceStatus((prevStatus) => {
            const nextStatus = { ...prevStatus };

            actions.forEach((action) => {
                if (!action || !action.topic) return;

                const targetDevice = devices.find((device) => device.topic === action.topic);

                if (targetDevice) {
                    const msg = action.message;
                    const isMotor = targetDevice.type === 'motor';

                    if (isMotor) {
                        try {
                            const jsonCmd = typeof msg === 'string' && msg.startsWith('{') ? JSON.parse(msg) : null;

                            if (jsonCmd) {
                                if (jsonCmd.speed !== undefined) {
                                    if (Number(jsonCmd.speed) > 0) {
                                        nextStatus[targetDevice.id] = `ON (${jsonCmd.speed}%)`;
                                    } else {
                                        nextStatus[targetDevice.id] = 'OFF';
                                    }
                                }
                            } else {
                                if (msg === 'ON' || msg === 'START') nextStatus[targetDevice.id] = 'ON';
                                else if (msg === 'OFF' || msg === 'STOP') nextStatus[targetDevice.id] = 'OFF';
                            }
                        } catch (error) {
                            console.warn('Error parsing motor command:', error);
                        }
                    } else {
                        const isTurningOn = msg === 'ON' || msg === '1' || msg === 'true';
                        nextStatus[targetDevice.id] = isTurningOn ? 'ON' : 'OFF';
                    }
                }
            });
            return nextStatus;
        });
    };

    useEffect(() => {
        fetchScenes();
    }, []);

    useEffect(() => {
        if (!socket) return;

        const handleProgress = (data) => {
            if (data && data.activeState) {
                setActiveState(data.activeState);
            }
        };

        socket.on('scene_progress', handleProgress);
        return () => socket.off('scene_progress', handleProgress);
    }, [socket]);

    useEffect(() => {
        timersRef.current.forEach((timer) => clearTimeout(timer));
        timersRef.current = [];

        if (activeState && sceneData && sceneData.states && sceneData.states[activeState]) {
            const stateNode = sceneData.states[activeState];

            if (stateNode.onEnter) {
                applyActions(stateNode.onEnter);
            }

            if (stateNode.timeline) {
                stateNode.timeline.forEach((item) => {
                    const delayMs = (item.at || 0) * 1000;

                    const timerId = setTimeout(() => {
                        const actionsToRun = item.actions ? item.actions : [item];
                        applyActions(actionsToRun);
                    }, delayMs);

                    timersRef.current.push(timerId);
                });
            }
        }

        return () => {
            timersRef.current.forEach((timer) => clearTimeout(timer));
            timersRef.current = [];
        };
    }, [activeState, sceneData]);

    const handleSelectScene = async (e) => {
        const filename = e.target.value;
        setSelectedScene(filename);
        if (filename) {
            const content = await loadSceneContent(filename);
            setSceneData(content);
            setActiveState(null);
            setSimulatedDeviceStatus({});

            timersRef.current.forEach((timer) => clearTimeout(timer));
            timersRef.current = [];
        }
    };

    const handlePlay = () => {
        if (selectedScene) {
            playScene(selectedScene);
            setActiveState(null);
            setSimulatedDeviceStatus({});
        }
    };

    const liveControls = (
        <div className="live-header-controls">
            <select
                className="live-select"
                onChange={handleSelectScene}
                value={selectedScene || ''}
            >
                <option value="" disabled>-- Vyber scénu --</option>
                {scenes.map((scene) => (
                    <option key={scene.name} value={scene.name}>{scene.name}</option>
                ))}
            </select>

            <Button
                variant="primary"
                icon={Play}
                onClick={handlePlay}
                disabled={!selectedScene}
            >
                Spustiť na RPi
            </Button>
            <Button
                variant="secondary"
                icon={RefreshCw}
                onClick={() => setSimulatedDeviceStatus({})}
                title="Resetovať zobrazenie zariadení"
            />
        </div>
    );

    const liveContent = (
        <>
            {embedded ? (
                <div className="live-view-inline-header">
                    <h2 className="live-view-inline-title">Live Testovanie</h2>
                    <p className="live-view-inline-subtitle">Sledovanie priebehu scény a stavu zariadení</p>
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
                            <SceneVisualizer data={sceneData} activeStateId={activeState} />
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
                        Live Status (Simulácia)
                    </div>

                    <div className="devices-list">
                        {devices.length === 0 ? (
                            <div className="text-muted text-sm p-4 text-center">
                                Žiadne zariadenia v devices.json
                            </div>
                        ) : (
                            devices.map((device) => {
                                const statusRaw = simulatedDeviceStatus[device.id];
                                const isOn = statusRaw === 'ON' || (typeof statusRaw === 'string' && statusRaw.includes('ON'));
                                const isRelay = device.type === 'relay';
                                const statusText = statusRaw || 'OFF';

                                return (
                                    <div key={device.id} className={`device-item ${isOn ? 'active' : ''}`}>
                                        <div className="device-info">
                                            <div className="device-icon">
                                                {isRelay ? <Power size={18} /> : <Cpu size={18} />}
                                            </div>
                                            <div>
                                                <div className="device-name">{device.name}</div>
                                                <div className="device-id">{device.id}</div>
                                            </div>
                                        </div>

                                        <div className="device-status">
                                            {statusText}
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
        return <div className="live-view-container live-view-embedded">{liveContent}</div>;
    }

    return (
        <div className="view-container live-view-container">
            {liveContent}
        </div>
    );
}
