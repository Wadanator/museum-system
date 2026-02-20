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
import SmartEdge from './SmartEdge';

// Import CSS pre vizualizér (ak nie je importovaný globálne, ale live-view.css ho rieši)
const nodeTypes = { custom: CustomFlowNode };
const edgeTypes = { smart: SmartEdge };

const STYLES = {
    default: { stroke: 'var(--secondary)', bg: 'var(--bg-hover)', color: 'var(--text-secondary)' },
    mqtt:    { stroke: 'var(--primary)',   bg: 'var(--bg-main)',  color: 'var(--primary)' },
    timeout: { stroke: 'var(--warning)',   bg: 'var(--warning-bg)', color: 'var(--warning-hover)' },
    audio:   { stroke: 'var(--info)',      bg: 'var(--info-bg)',    color: 'var(--info-hover)' },
    video:   { stroke: '#ec4899',          bg: '#fce7f3',           color: '#be185d' },
};

export default function SceneVisualizer({ data, activeStateId }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    const formatAnyAction = (a) => {
        if (!a) return 'Neznámy príkaz';
        if (a.action === 'mqtt') return `${a.topic} ➔ ${a.message}`;
        if (a.action === 'audio' || a.action === 'video') return `${a.action.toUpperCase()}: ${a.message}`;
        return `${a.action || 'cmd'}: ${a.message || (a.topic ? a.topic : JSON.stringify(a))}`;
    };

    const parseStateData = (stateData) => {
        const sections = { onEnter: [], timeline: [], transitions: [] };
        if (stateData.onEnter) stateData.onEnter.forEach(a => sections.onEnter.push(formatAnyAction(a)));
        if (stateData.timeline) {
            stateData.timeline.forEach(t => {
                const actions = t.actions || (t.action ? [t] : []);
                actions.forEach(a => sections.timeline.push({ time: t.at, text: formatAnyAction(a) }));
            });
        }
        if (stateData.transitions) {
            stateData.transitions.forEach(tr => {
                let desc = tr.type === 'timeout' ? `⏱️ Po ${tr.delay}s` : `📩 ${tr.type}`;
                sections.transitions.push(`${desc} ➔ GOTO: ${tr.goto}`);
            });
        }
        return sections;
    };

    const calculateLayout = useCallback(() => {
        if (!data || !data.states) return;

        const newNodes = [];
        const newEdges = [];
        const stateKeys = Object.keys(data.states);
        const startState = data.initialState || stateKeys[0];

        // --- BFS Layout ---
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

            data.states[id]?.transitions?.forEach(t => {
                if (t.goto !== 'END' && data.states[t.goto] && !visited.has(t.goto)) {
                    queue.push({ id: t.goto, level: level + 1 });
                }
            });
        }

        stateKeys.forEach(key => {
            if (!visited.has(key)) {
                const orphanLevel = maxDepth + 1;
                if (!levels[orphanLevel]) levels[orphanLevel] = [];
                levels[orphanLevel].push(key);
            }
        });

        // --- Nodes ---
        const NODE_WIDTH = 420; 
        const LEVEL_HEIGHT = 450; 

        Object.entries(levels).forEach(([levelStr, stateIds]) => {
            const level = parseInt(levelStr);
            const startX = -(stateIds.length * NODE_WIDTH / 2) + (NODE_WIDTH / 2);

            stateIds.forEach((stateId, index) => {
                const stateData = data.states[stateId];
                const isActive = stateId === activeStateId;
                
                newNodes.push({
                    id: stateId,
                    type: 'custom',
                    position: { x: startX + (index * NODE_WIDTH), y: level * LEVEL_HEIGHT },
                    // TU SA POUŽÍVA CSS TRIEDA
                    className: isActive ? 'node-active' : '',
                    data: {
                        label: stateId,
                        type: stateId === startState ? 'start' : 'step',
                        description: stateData?.description || '',
                        sections: parseStateData(stateData),
                        transitionCount: stateData?.transitions?.length || 0
                    }
                });
            });
        });

        // End Node
        if (stateKeys.some(k => data.states[k]?.transitions?.some(t => t.goto === 'END'))) {
            const isEndActive = activeStateId === 'END';
            newNodes.push({
                id: 'END',
                type: 'custom',
                position: { x: 0, y: (maxDepth + 1) * LEVEL_HEIGHT + 100 },
                className: isEndActive ? 'node-active' : '',
                data: { label: 'KONIEC', type: 'end', transitionCount: 0 }
            });
        }

        // --- Edges ---
        stateKeys.forEach(stateName => {
            data.states[stateName].transitions?.forEach((trans, idx) => {
                let styleConfig = STYLES.default;
                if (trans.type === 'mqttMessage') styleConfig = STYLES.mqtt;
                else if (trans.type === 'timeout') styleConfig = STYLES.timeout;
                else if (trans.type === 'audioEnd') styleConfig = STYLES.audio;
                else if (trans.type === 'videoEnd') styleConfig = STYLES.video;

                newEdges.push({
                    id: `e-${stateName}-${trans.goto}-${idx}`,
                    source: stateName,
                    target: trans.goto,
                    sourceHandle: `handle-${idx}`,
                    type: 'smart',
                    label: trans.type === 'timeout' ? `⏱️ ${trans.delay}s` : '',
                    style: { stroke: styleConfig.stroke, strokeWidth: 2 },
                    markerEnd: { type: MarkerType.ArrowClosed, color: styleConfig.stroke },
                    animated: activeStateId === stateName
                });
            });
        });

        setNodes(newNodes);
        setEdges(newEdges);
    }, [data, setNodes, setEdges, activeStateId]);

    useEffect(() => { calculateLayout(); }, [calculateLayout]);

    return (
        <div className="flow-wrapper">
            <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} nodeTypes={nodeTypes} edgeTypes={edgeTypes} fitView>
                <Background color="var(--border-color)" gap={30} size={1} />
                <Controls showInteractive={false} />
                <Panel position="top-right" className="flow-legend-panel">
                    <div className="legend-title">Legenda prechodov</div>
                    <div className="legend-item"><div className="legend-dot dot-mqtt"></div><span>MQTT</span></div>
                    <div className="legend-item"><div className="legend-dot dot-timeout"></div><span>Časovač</span></div>
                    <div className="legend-item"><div className="legend-dot dot-audio"></div><span>Audio koniec</span></div>
                    <div className="legend-item"><div className="legend-dot dot-video"></div><span>Video koniec</span></div>
                </Panel>
            </ReactFlow>
        </div>
    );
}