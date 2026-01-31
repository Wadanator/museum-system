import { useState, useEffect } from 'react';
import { useSocket } from '../../context/SocketContext';
import { useScenes } from '../../hooks/useScenes';
import { useDevices } from '../../hooks/useDevices';
import SceneVisualizer from '../Scenes/SceneVisualizer';
import PageHeader from '../ui/PageHeader';
import Button from '../ui/Button';
import { Activity, Play, Zap, Power, Cpu, RefreshCw } from 'lucide-react';

// Import nového CSS
import '../../styles/views/live-view.css';

export default function LiveView() {
    const { socket } = useSocket();
    const { scenes, loadSceneContent, playScene, fetchScenes } = useScenes();
    const { devices } = useDevices(); 
    
    const [selectedScene, setSelectedScene] = useState(null);
    const [sceneData, setSceneData] = useState(null);
    const [activeState, setActiveState] = useState(null);
    
    // Stav pre simuláciu (ID zariadenia -> textový stav alebo bool)
    const [simulatedDeviceStatus, setSimulatedDeviceStatus] = useState({});

    useEffect(() => {
        fetchScenes();
    }, []);

    // 1. Socket Listener
    useEffect(() => {
        if (!socket) return;
        
        const handleProgress = (data) => {
            if (data && data.activeState) {
                setActiveState(data.activeState);
                if (sceneData && sceneData.states && sceneData.states[data.activeState]) {
                    updateDevicesFromState(sceneData.states[data.activeState]);
                }
            }
        };

        socket.on('scene_progress', handleProgress);
        return () => socket.off('scene_progress', handleProgress);
    }, [socket, sceneData]); 

    // 2. Logika pre aktualizáciu zariadení (Motory aj Relé)
    const updateDevicesFromState = (stateNode) => {
        const newUpdates = {};
        
        const processAction = (action) => {
            if (!action || !action.topic) return;
            
            // Nájdi zariadenie podľa topicu
            const targetDevice = devices.find(d => d.topic === action.topic);
            
            if (targetDevice) {
                const msg = action.message;
                const isMotor = targetDevice.type === 'motor'; // Predpokladáme, že devices.json má typ 'motor'

                if (isMotor) {
                    // --- LOGIKA PRE MOTORY (Parsuje JSON) ---
                    try {
                        // Skúsime či je to JSON objekt {"speed": 50}
                        const jsonCmd = typeof msg === 'string' && msg.startsWith('{') ? JSON.parse(msg) : null;
                        
                        if (jsonCmd) {
                            if (jsonCmd.speed !== undefined) {
                                // Ak je rýchlosť > 0, je ON
                                if (Number(jsonCmd.speed) > 0) {
                                    newUpdates[targetDevice.id] = `ON (${jsonCmd.speed}%)`;
                                } else {
                                    newUpdates[targetDevice.id] = "OFF";
                                }
                            }
                        } else {
                            // Fallback pre jednoduché príkazy "ON" / "OFF" / "START"
                            if (msg === "ON" || msg === "START") newUpdates[targetDevice.id] = "ON";
                            else if (msg === "OFF" || msg === "STOP") newUpdates[targetDevice.id] = "OFF";
                        }
                    } catch (e) {
                        console.warn("Chyba parsovania motor príkazu:", e);
                    }
                } else {
                    // --- LOGIKA PRE RELÉ (Jednoduché ON/OFF) ---
                    const isTurningOn = msg === "ON" || msg === "1" || msg === "true";
                    newUpdates[targetDevice.id] = isTurningOn ? "ON" : "OFF";
                }
            }
        };

        // Spracuj onEnter
        if (stateNode.onEnter) {
            stateNode.onEnter.forEach(processAction);
        }
        // Spracuj Timeline
        if (stateNode.timeline) {
            stateNode.timeline.forEach(item => {
                if (item.actions) item.actions.forEach(processAction);
                else if (item.action) processAction(item);
            });
        }

        // Ulož do stavu (zachovaj staré, prepíš nové)
        setSimulatedDeviceStatus(prev => ({
            ...prev,
            ...newUpdates
        }));
    };

    const handleSelectScene = async (e) => {
        const filename = e.target.value;
        setSelectedScene(filename);
        if (filename) {
            const content = await loadSceneContent(filename);
            setSceneData(content);
            setActiveState(null);
            setSimulatedDeviceStatus({});
        }
    };

    const handlePlay = () => {
        if (selectedScene) {
            playScene(selectedScene);
            setActiveState(null); 
            setSimulatedDeviceStatus({});
        }
    };

    return (
        <div className="view-container live-view-container">
            <PageHeader 
                title="Live Testovanie" 
                icon={Activity} 
                subtitle="Sledovanie priebehu scény a stavu zariadení"
            >
                <div className="live-header-controls">
                    <select 
                        className="live-select"
                        onChange={handleSelectScene}
                        value={selectedScene || ""}
                    >
                        <option value="" disabled>-- Vyber scénu --</option>
                        {scenes.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
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
            </PageHeader>

            <div className="live-grid">
                {/* 1. VIZUALIZÉR */}
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

                {/* 2. PANEL ZARIADENÍ */}
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
                            devices.map(device => {
                                const statusRaw = simulatedDeviceStatus[device.id];
                                // Zistíme či je zapnuté (ak je status "ON" alebo string s %)
                                const isOn = statusRaw === "ON" || (typeof statusRaw === 'string' && statusRaw.includes("ON"));
                                const isRelay = device.type === 'relay';
                                
                                // Display text: Ak nemáme status, je OFF. Ak máme, ukážeme ho (napr "ON (50%)")
                                const statusText = statusRaw || "OFF";

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
        </div>
    );
}