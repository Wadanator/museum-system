import { useEffect } from 'react';
import ReactFlow, { 
    Background, 
    Controls, 
    useNodesState, 
    useEdgesState,
    MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import CustomFlowNode from './CustomFlowNode';

const nodeTypes = {
    custom: CustomFlowNode,
};

// ARCHITECTURE FIX: Definícia farieb v konštante namiesto hardcoded stringov
const FLOW_COLORS = {
    mqtt: '#8b5cf6',      // Violet-500
    timeout: '#f59e0b',   // Amber-500
    audio: '#0ea5e9',     // Sky-500
    default: '#94a3b8'    // Slate-400
};

export default function SceneVisualizer({ data }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    useEffect(() => {
        if (!data || !data.states) {
            setNodes([]);
            setEdges([]);
            return;
        }

        const newNodes = [];
        const newEdges = [];
        
        // --- 1. PRÍPRAVA DÁT ---
        const stateKeys = Object.keys(data.states);
        const startState = data.initialState || stateKeys[0];
        let hasEnd = false;

        const parseActions = (stateData) => {
            const list = [];
            if (stateData.onEnter) {
                stateData.onEnter.forEach(a => {
                    let val = a.action;
                    if (a.action === 'mqtt') val = `${a.topic} -> ${a.message}`;
                    if (a.action === 'audio' || a.action === 'video') val = a.message;
                    list.push({ type: a.action, val });
                });
            }
            if (stateData.timeline) {
                stateData.timeline.forEach(t => {
                     list.push({ type: 'clock', val: `Wait ${t.at}s: ${t.action}` });
                });
            }
            return list;
        };

        // --- 2. VÝPOČET LAYOUTU ---
        const levels = {};
        const visited = new Set();
        const queue = [{ id: startState, level: 0 }];
        
        stateKeys.forEach(k => visited.add(k));
        visited.clear();

        while (queue.length > 0) {
            const { id, level } = queue.shift();
            if (visited.has(id)) continue;
            visited.add(id);

            if (!levels[level]) levels[level] = [];
            levels[level].push(id);

            const state = data.states[id];
            if (state && state.transitions) {
                state.transitions.forEach(t => {
                    if (t.goto === 'END') {
                        hasEnd = true;
                    } else if (data.states[t.goto]) {
                        queue.push({ id: t.goto, level: level + 1 });
                    }
                });
            }
        }

        stateKeys.forEach(key => {
            if (!visited.has(key)) {
                const lastLevel = Math.max(...Object.keys(levels).map(Number), 0) + 1;
                if (!levels[lastLevel]) levels[lastLevel] = [];
                levels[lastLevel].push(key);
            }
        });

        // --- 3. GENEROVANIE NODES ---
        const NODE_WIDTH = 280;
        
        Object.entries(levels).forEach(([levelStr, stateIds]) => {
            const level = parseInt(levelStr);
            const count = stateIds.length;
            const totalWidth = count * NODE_WIDTH;
            const startX = -(totalWidth / 2) + (NODE_WIDTH / 2);

            stateIds.forEach((stateId, index) => {
                const stateData = data.states[stateId];
                const isStart = stateId === startState;
                
                newNodes.push({
                    id: stateId,
                    type: 'custom',
                    position: { 
                        x: startX + (index * NODE_WIDTH), 
                        y: level * 250 + 50 
                    },
                    data: {
                        label: stateId,
                        type: isStart ? 'start' : 'step',
                        description: stateData.description,
                        actions: parseActions(stateData)
                    }
                });
            });
        });

        if (hasEnd) {
            const lastLevel = Math.max(...Object.keys(levels).map(Number), 0);
            newNodes.push({
                id: 'END',
                type: 'custom',
                position: { x: 0, y: (lastLevel + 1) * 250 + 50 },
                data: {
                    label: 'KONIEC SCÉNY',
                    type: 'end',
                    description: 'Ukončenie behu scény'
                }
            });
        }

        // --- 4. GENEROVANIE EDGES ---
        stateKeys.forEach(stateName => {
            const stateData = data.states[stateName];
            if (stateData.transitions) {
                stateData.transitions.forEach((trans, idx) => {
                    const target = trans.goto;
                    
                    let color = FLOW_COLORS.default;
                    let label = '';
                    
                    if (trans.type === 'mqttMessage') { 
                        color = FLOW_COLORS.mqtt; 
                        label = trans.message || 'Button'; 
                    }
                    else if (trans.type === 'timeout') { 
                        color = FLOW_COLORS.timeout; 
                        label = `${trans.delay}s`; 
                    }
                    else if (trans.type === 'audioEnd') { 
                        color = FLOW_COLORS.audio; 
                        label = 'Audio End'; 
                    }

                    newEdges.push({
                        id: `e-${stateName}-${target}-${idx}`,
                        source: stateName,
                        target: target,
                        type: 'smoothstep',
                        label: label,
                        style: { stroke: color, strokeWidth: 2 },
                        labelStyle: { fill: color, fontWeight: 700, fontSize: 11 },
                        markerEnd: { type: MarkerType.ArrowClosed, color: color }
                    });
                });
            }
        });

        setNodes(newNodes);
        setEdges(newEdges);

    }, [data, setNodes, setEdges]);

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-right"
            minZoom={0.1}
        >
            <Background color="#cbd5e1" gap={20} />
            <Controls />
        </ReactFlow>
    );
}