import { useEffect, useCallback } from 'react';
import ReactFlow, { 
    Background, 
    Controls, 
    useNodesState, 
    useEdgesState,
    MarkerType,
    Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import CustomFlowNode from './CustomFlowNode';
// Importujeme SmartEdge (uistite sa, že tento súbor existuje podľa predchádzajúceho kroku)
import SmartEdge from './SmartEdge';

const nodeTypes = {
    custom: CustomFlowNode,
};

// Registrácia nášho nového typu čiary
const edgeTypes = {
    smart: SmartEdge,
};

// Definícia farieb pre legendu a čiary
const STYLES = {
    default: { stroke: '#94a3b8', bg: '#f1f5f9', color: '#475569' },
    mqtt:    { stroke: '#6366f1', bg: '#e0e7ff', color: '#4338ca' }, // Indigo
    timeout: { stroke: '#f59e0b', bg: '#fffbeb', color: '#b45309' }, // Amber
    audio:   { stroke: '#06b6d4', bg: '#ecfeff', color: '#0e7490' }, // Cyan
    video:   { stroke: '#ec4899', bg: '#fce7f3', color: '#be185d' }, // Pink
};

export default function SceneVisualizer({ data }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    const calculateLayout = useCallback(() => {
        if (!data || !data.states) {
            setNodes([]);
            setEdges([]);
            return;
        }

        const newNodes = [];
        const newEdges = [];
        const stateKeys = Object.keys(data.states);
        const startState = data.initialState || stateKeys[0];

        // --- 1. PARSOVANIE AKCIÍ PRE NODE ---
        const parseActions = (stateData) => {
            const list = [];
            // On Enter
            if (stateData.onEnter) {
                stateData.onEnter.forEach(a => {
                    let val = a.action;
                    if (a.action === 'mqtt') val = `${a.topic} ➔ ${a.message}`;
                    if (a.action === 'audio') val = `🎵 ${a.message}`;
                    if (a.action === 'video') val = `🎬 ${a.message}`;
                    list.push({ type: a.action, val });
                });
            }
            // Timeline
            if (stateData.timeline) {
                stateData.timeline.forEach(t => {
                     let desc = t.action;
                     if (t.action === 'mqtt') desc = `${t.topic} ➔ ${t.message}`;
                     else if (t.action === 'audio') desc = `Audio: ${t.message}`;
                     list.push({ type: 'clock', val: `+${t.at}s: ${desc}` });
                });
            }
            return list;
        };

        // --- 2. VÝPOČET LEVELOV (BFS) ---
        const levels = {};
        const visited = new Set();
        const queue = [{ id: startState, level: 0 }];
        let maxDepth = 0;

        while (queue.length > 0) {
            const { id, level } = queue.shift();
            if (visited.has(id)) continue;
            visited.add(id);

            if (!levels[level]) levels[level] = [];
            levels[level].push(id);
            if (level > maxDepth) maxDepth = level;

            const state = data.states[id];
            if (state && state.transitions) {
                state.transitions.forEach(t => {
                    if (t.goto !== 'END' && data.states[t.goto] && !visited.has(t.goto)) {
                        queue.push({ id: t.goto, level: level + 1 });
                    }
                });
            }
        }
        // Siroty
        stateKeys.forEach(key => {
            if (!visited.has(key)) {
                const orphanLevel = maxDepth + 1;
                if (!levels[orphanLevel]) levels[orphanLevel] = [];
                levels[orphanLevel].push(key);
            }
        });

        // --- 3. GENEROVANIE NODES ---
        const NODE_WIDTH = 380; 
        const LEVEL_HEIGHT = 350; 

        Object.entries(levels).forEach(([levelStr, stateIds]) => {
            const level = parseInt(levelStr);
            const startX = -(stateIds.length * NODE_WIDTH / 2) + (NODE_WIDTH / 2);

            stateIds.forEach((stateId, index) => {
                const stateData = data.states[stateId];
                // Spočítame výstupy pre dynamické handles
                const transCount = stateData.transitions ? stateData.transitions.length : 0;

                newNodes.push({
                    id: stateId,
                    type: 'custom',
                    position: { 
                        x: startX + (index * NODE_WIDTH), 
                        y: level * LEVEL_HEIGHT + 50 
                    },
                    data: {
                        label: stateId,
                        type: stateId === startState ? 'start' : 'step',
                        description: stateData.description,
                        actions: parseActions(stateData),
                        transitionCount: transCount 
                    }
                });
            });
        });

        // End Node
        let hasEnd = false;
        stateKeys.forEach(k => data.states[k]?.transitions?.forEach(t => { if(t.goto === 'END') hasEnd = true; }));
        if (hasEnd) {
            newNodes.push({
                id: 'END',
                type: 'custom',
                position: { x: 0, y: (maxDepth + 1) * LEVEL_HEIGHT + 100 },
                data: { label: 'KONIEC', type: 'end', transitionCount: 0 }
            });
        }

        // --- 4. GENEROVANIE EDGES (SMART) ---
        stateKeys.forEach(stateName => {
            const stateData = data.states[stateName];
            if (stateData.transitions) {
                stateData.transitions.forEach((trans, idx) => {
                    const target = trans.goto;
                    
                    let styleConfig = STYLES.default;
                    let label = '';
                    let animated = false;
                    let strokeDasharray = '0';

                    if (trans.type === 'mqttMessage') { 
                        styleConfig = STYLES.mqtt;
                        const topic = trans.topic || 'mqtt';
                        const msg = trans.message || '*';
                        label = `📩 ${topic} ➔ ${msg}`; 
                    }
                    else if (trans.type === 'timeout') { 
                        styleConfig = STYLES.timeout;
                        label = `⏱️ Po ${trans.delay}s`; 
                        animated = true;
                        strokeDasharray = '5 5';
                    }
                    else if (trans.type === 'audioEnd') { 
                        styleConfig = STYLES.audio;
                        const audioAction = stateData.onEnter?.find(a => a.action === 'audio');
                        const fileName = audioAction ? audioAction.message : '???';
                        label = `🎵 Koniec: ${fileName}`; 
                    }
                    else if (trans.type === 'videoEnd') { 
                        styleConfig = STYLES.video;
                        label = `🎬 Video End`; 
                    }

                    newEdges.push({
                        id: `e-${stateName}-${target}-${idx}`,
                        source: stateName,
                        target: target,
                        sourceHandle: `handle-${idx}`, // Pripájame na konkrétny handle
                        type: 'smart',                 // Používame našu novú Smart čiaru
                        label: label,
                        animated: animated,
                        style: { 
                            stroke: styleConfig.stroke, 
                            strokeWidth: 2,
                            strokeDasharray: strokeDasharray
                        },
                        // SmartEdge props:
                        labelStyle: { 
                            color: styleConfig.color, // Farba textu
                        },
                        labelBgStyle: { 
                            fill: styleConfig.bg,     // Farba bubliny
                            stroke: styleConfig.stroke,
                        },
                        markerEnd: { type: MarkerType.ArrowClosed, color: styleConfig.stroke }
                    });
                });
            }
        });

        setNodes(newNodes);
        setEdges(newEdges);
    }, [data, setNodes, setEdges]);

    useEffect(() => {
        calculateLayout();
    }, [calculateLayout]);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes} 
            fitView
            minZoom={0.1}
            maxZoom={1.5}
        >
            <Background color="var(--border-color)" gap={30} size={1} />
            <Controls showInteractive={false} />
            
            {/* LEGENDA - Presunutá do Top Right */}
            <Panel position="top-right" style={{ 
                background: 'var(--bg-card)', 
                padding: '12px 16px', 
                borderRadius: '8px', 
                border: '1px solid var(--border-color)',
                fontSize: '0.8rem', 
                color: 'var(--text-secondary)',
                boxShadow: 'var(--shadow-md)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
            }}>
                <div style={{ fontWeight: 'bold', borderBottom: '1px solid var(--border-color)', paddingBottom: '4px' }}>
                    Legenda prechodov:
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: STYLES.mqtt.stroke }}></div>
                    <span>MQTT / Tlačidlo</span>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: STYLES.timeout.stroke, border: '1px dashed #fff' }}></div>
                    <span>Časovač (Automaticky)</span>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: STYLES.audio.stroke }}></div>
                    <span>Audio / Video koniec</span>
                </div>
            </Panel>
        </ReactFlow>
    );
}