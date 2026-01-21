import { useEffect, useCallback } from 'react';
import ReactFlow, { 
    Background, 
    Controls, 
    useNodesState, 
    useEdgesState,
    addEdge,
    MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import CustomFlowNode from './CustomFlowNode';

const nodeTypes = {
    custom: CustomFlowNode,
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

        // Pomocná funkcia na parsovanie akcií pre zobrazenie
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
            // Pridanie Timeline eventov ak existujú
            if (stateData.timeline) {
                stateData.timeline.forEach(t => {
                     list.push({ type: 'clock', val: `Wait ${t.at}s: ${t.action}` });
                });
            }
            return list;
        };

        // --- 2. VÝPOČET LAYOUTU (BFS ALGORITMUS) ---
        // Cieľ: Rozdeliť stavy do "poschodí" (levels) podľa vzdialenosti od štartu
        const levels = {}; // { 0: ['start'], 1: ['volba1', 'volba2'], ... }
        const visited = new Set();
        const queue = [{ id: startState, level: 0 }];
        
        // Inicializácia levels
        stateKeys.forEach(k => visited.add(k)); // Označíme všetky ako "poznáme", neskôr prejdeme
        visited.clear(); // Reset pre BFS

        // BFS prepojených uzlov
        while (queue.length > 0) {
            const { id, level } = queue.shift();
            if (visited.has(id)) continue;
            visited.add(id);

            if (!levels[level]) levels[level] = [];
            levels[level].push(id);

            // Nájdi susedov (transitions)
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

        // Pridanie neprepojených uzlov (orphan nodes) na koniec, aby nezmizli
        stateKeys.forEach(key => {
            if (!visited.has(key)) {
                const lastLevel = Math.max(...Object.keys(levels).map(Number), 0) + 1;
                if (!levels[lastLevel]) levels[lastLevel] = [];
                levels[lastLevel].push(key);
            }
        });

        // --- 3. GENEROVANIE NODES PODĽA LAYOUTU ---
        const NODE_WIDTH = 280;
        const NODE_HEIGHT = 150; // Odhadovaná výška pre mriežku
        
        Object.entries(levels).forEach(([levelStr, stateIds]) => {
            const level = parseInt(levelStr);
            const count = stateIds.length;
            
            // Vycentrovanie riadku: (celková šírka / 2)
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

        // --- 4. PRIDANIE "END" NODE ---
        if (hasEnd) {
            const lastLevel = Math.max(...Object.keys(levels).map(Number), 0);
            newNodes.push({
                id: 'END',
                type: 'custom',
                position: { x: 0, y: (lastLevel + 1) * 250 + 50 }, // Vždy v strede pod všetkým
                data: {
                    label: 'KONIEC SCÉNY',
                    type: 'end',
                    description: 'Ukončenie behu scény'
                }
            });
        }

        // --- 5. GENEROVANIE HRÁN (EDGES) ---
        stateKeys.forEach(stateName => {
            const stateData = data.states[stateName];
            if (stateData.transitions) {
                stateData.transitions.forEach((trans, idx) => {
                    const target = trans.goto;
                    
                    // Štýly pre hrany
                    let color = '#94a3b8';
                    let label = '';
                    
                    if (trans.type === 'mqttMessage') { color = '#8b5cf6'; label = trans.message || 'Button'; } // Violet
                    else if (trans.type === 'timeout') { color = '#f59e0b'; label = `${trans.delay}s`; } // Amber
                    else if (trans.type === 'audioEnd') { color = '#0ea5e9'; label = 'Audio End'; } // Sky

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