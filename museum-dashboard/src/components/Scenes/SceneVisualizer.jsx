import { useEffect, useCallback, useRef, useState } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType,
    Panel,
    useReactFlow,
    ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import CustomFlowNode from './CustomFlowNode';
import SmartEdge from './SmartEdge';
import { Maximize2, Minimize2, ScanSearch } from 'lucide-react';
import Button from '../ui/Button';

const nodeTypes = { custom: CustomFlowNode };
const edgeTypes  = { smart: SmartEdge };

// Edge stroke colors are read from CSS variables at layout time so we
// never hardcode hex values here.
const EDGE_CSS_VAR = {
    default:     '--secondary',
    mqttMessage: '--primary',
    timeout:     '--warning',
    audioEnd:    '--info',
    videoEnd:    '--color-video',  // defined in scene-flow.css :root
};

function getCSSVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ─── Inner component (needs useReactFlow which requires a Provider above) ──
function SceneVisualizerInner({ data, activeStateId }) {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const { fitView } = useReactFlow();
    const wrapperRef = useRef(null);

    // ── Helpers ─────────────────────────────────────────────────────────────

    const formatAnyAction = (a) => {
        if (!a) return 'Neznámy príkaz';
        if (a.action === 'mqtt') return `${a.topic} ➔ ${a.message}`;
        if (a.action === 'audio' || a.action === 'video')
            return `${a.action.toUpperCase()}: ${a.message}`;
        return `${a.action || 'cmd'}: ${a.message || a.topic || JSON.stringify(a)}`;
    };

    // ── Layout (BFS) ─────────────────────────────────────────────────────────

    const calculateLayout = useCallback(() => {
        if (!data?.states) return;

        const parseStateData = (stateData) => {
            const s = { onEnter: [], onExit: [], timeline: [], transitions: [] };
            stateData.onEnter?.forEach(a => s.onEnter.push(formatAnyAction(a)));
            stateData.onExit?.forEach(a  => s.onExit.push(formatAnyAction(a)));
            stateData.timeline?.forEach(t => {
                const actions = t.actions || (t.action ? [t] : []);
                actions.forEach(a => s.timeline.push({ time: t.at, text: formatAnyAction(a) }));
            });
            stateData.transitions?.forEach(tr => {
                const desc = tr.type === 'timeout' ? `⏱️ Po ${tr.delay}s` : `📩 ${tr.type}`;
                s.transitions.push(`${desc} ➔ GOTO: ${tr.goto}`);
            });
            return s;
        };

        const newNodes   = [];
        const newEdges   = [];
        const stateKeys  = Object.keys(data.states);
        const startState = data.initialState || stateKeys[0];

        // BFS to assign depth levels
        const levels  = {};
        const visited = new Set();
        const queue   = [{ id: startState, level: 0 }];
        let maxDepth  = 0;

        while (queue.length > 0) {
            const { id, level } = queue.shift();
            if (visited.has(id)) continue;
            visited.add(id);
            if (!levels[level]) levels[level] = [];
            levels[level].push(id);
            if (level > maxDepth) maxDepth = level;
            data.states[id]?.transitions?.forEach(t => {
                if (t.goto !== 'END' && data.states[t.goto] && !visited.has(t.goto))
                    queue.push({ id: t.goto, level: level + 1 });
            });
        }

        // Orphan nodes (unreachable from start) go on their own row
        stateKeys.forEach(key => {
            if (!visited.has(key)) {
                const lvl = maxDepth + 1;
                if (!levels[lvl]) levels[lvl] = [];
                levels[lvl].push(key);
            }
        });

        const NODE_WIDTH   = 360;
        const LEVEL_HEIGHT = 430;
        const H_GAP        = 40;

        Object.entries(levels).forEach(([levelStr, stateIds]) => {
            const level      = parseInt(levelStr);
            const totalWidth = stateIds.length * NODE_WIDTH + (stateIds.length - 1) * H_GAP;
            const startX     = -(totalWidth / 2) + NODE_WIDTH / 2;

            stateIds.forEach((stateId, index) => {
                const stateData    = data.states[stateId];
                const sections     = parseStateData(stateData);
                const totalActions = sections.onEnter.length + sections.onExit.length + sections.timeline.length;

                newNodes.push({
                    id: stateId,
                    type: 'custom',
                    position: { x: startX + index * (NODE_WIDTH + H_GAP), y: level * LEVEL_HEIGHT },
                    className: '',
                    data: {
                        label: stateId,
                        type: stateId === startState ? 'start' : 'step',
                        description: stateData?.description || '',
                        sections,
                        transitionCount: stateData?.transitions?.length || 0,
                        totalActions,
                    },
                });
            });
        });

        // END sentinel node
        if (stateKeys.some(k => data.states[k]?.transitions?.some(t => t.goto === 'END'))) {
            newNodes.push({
                id: 'END',
                type: 'custom',
                position: { x: 0, y: (maxDepth + 1) * LEVEL_HEIGHT + 80 },
                className: '',
                data: { label: 'KONIEC', type: 'end', transitionCount: 0 },
            });
        }

        // Edges
        stateKeys.forEach(stateName => {
            data.states[stateName].transitions?.forEach((trans, idx) => {
                const varName     = EDGE_CSS_VAR[trans.type] ?? EDGE_CSS_VAR.default;
                const strokeColor = getCSSVar(varName) || 'var(--secondary)';
                newEdges.push({
                    id: `e-${stateName}-${trans.goto}-${idx}`,
                    source: stateName,
                    target: trans.goto,
                    sourceHandle: `handle-${idx}`,
                    type: 'smart',
                    label: trans.type === 'timeout' ? `⏱️ ${trans.delay}s` : '',
                    style: { stroke: strokeColor, strokeWidth: 2 },
                    markerEnd: { type: MarkerType.ArrowClosed, color: strokeColor },
                    animated: false,
                });
            });
        });

        setNodes(newNodes);
        setEdges(newEdges);
    }, [data, setNodes, setEdges]);

    useEffect(() => { calculateLayout(); }, [calculateLayout]);

    // ── Active-state patch — only updates className/animated, no re-layout ───
    useEffect(() => {
        setNodes(nds => nds.map(n => ({
            ...n,
            className: n.id === activeStateId ? 'node-active' : '',
        })));
        setEdges(eds => eds.map(e => ({
            ...e,
            animated: e.source === activeStateId,
        })));
    }, [activeStateId, setNodes, setEdges]);

    // ── fitView — fires only when scene changes (node count changes) ─────────
    //
    // KEY FIX: dependency is [nodes] but we guard with prevNodeCountRef.
    // - expand/collapse  → same node count → skipped ✓
    // - drag             → same node count → skipped ✓
    // - activeStateId    → same node count → skipped ✓
    // - new scene loaded → count changes   → fitView fires ✓
    const prevNodeCountRef = useRef(0);
    useEffect(() => {
        const count = nodes.length;
        if (count === 0 || count === prevNodeCountRef.current) return;
        prevNodeCountRef.current = count;
        const t = setTimeout(() => fitView({ padding: 0.15, duration: 400 }), 50);
        return () => clearTimeout(t);
    }, [nodes, fitView]);

    // ── Fullscreen ───────────────────────────────────────────────────────────
    const fullscreenTimerRef = useRef(null);

    const toggleFullscreen = useCallback(() => {
        clearTimeout(fullscreenTimerRef.current);
        setIsFullscreen(prev => !prev);
        fullscreenTimerRef.current = setTimeout(
            () => fitView({ padding: 0.15, duration: 300 }), 350
        );
    }, [fitView]);

    useEffect(() => () => clearTimeout(fullscreenTimerRef.current), []);

    useEffect(() => {
        const onKey = (e) => { if (e.key === 'Escape' && isFullscreen) setIsFullscreen(false); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [isFullscreen]);

    // ── Render ───────────────────────────────────────────────────────────────
    return (
        <div
            ref={wrapperRef}
            className={`flow-wrapper${isFullscreen ? ' flow-fullscreen' : ''}`}
            onWheel={(e) => e.stopPropagation()}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                minZoom={0.05}
                maxZoom={2}
                attributionPosition="bottom-left"
                preventScrolling
                panOnDrag
                nodeDragThreshold={5}
                zoomOnScroll
                zoomOnPinch
                panOnScroll={false}
            >
                <Background color="var(--border-color)" gap={24} size={1.5} variant="dots" />
                <Controls showInteractive={false} />

                <MiniMap
                    className="flow-minimap"
                    maskColor="var(--minimap-mask)"
                    nodeColor={(n) => {
                        if (n.data?.type === 'start')             return getCSSVar('--success')  || 'var(--success)';
                        if (n.data?.type === 'end')               return getCSSVar('--danger')   || 'var(--danger)';
                        if (n.className?.includes('node-active')) return getCSSVar('--primary')  || 'var(--primary)';
                        return getCSSVar('--secondary') || 'var(--secondary)';
                    }}
                />

                <Panel position="top-right" className="flow-top-panel">
                    <Button
                        className="flow-icon-btn"
                        variant="ghost"
                        size="small"
                        icon={ScanSearch}
                        onClick={() => fitView({ padding: 0.15, duration: 400 })}
                        title="Prispôsobiť zobrazenie"
                        aria-label="Prispôsobiť zobrazenie"
                    />
                    <Button
                        className="flow-icon-btn"
                        variant="ghost"
                        size="small"
                        icon={isFullscreen ? Minimize2 : Maximize2}
                        onClick={toggleFullscreen}
                        title={isFullscreen ? 'Zatvoriť (Esc)' : 'Celá obrazovka'}
                        aria-label={isFullscreen ? 'Zatvoriť celú obrazovku' : 'Celá obrazovka'}
                    />
                </Panel>

                <Panel position="bottom-left" className="flow-legend-panel">
                    <div className="legend-title">Prechody</div>
                    <div className="legend-item"><div className="legend-dot dot-mqtt"></div><span>MQTT</span></div>
                    <div className="legend-item"><div className="legend-dot dot-timeout"></div><span>Časovač</span></div>
                    <div className="legend-item"><div className="legend-dot dot-audio"></div><span>Audio koniec</span></div>
                    <div className="legend-item"><div className="legend-dot dot-video"></div><span>Video koniec</span></div>
                </Panel>
            </ReactFlow>
        </div>
    );
}

// ─── Public export ──────────────────────────────────────────────────────────
export default function SceneVisualizer({ data, activeStateId }) {
    return (
        <ReactFlowProvider>
            <SceneVisualizerInner data={data} activeStateId={activeStateId} />
        </ReactFlowProvider>
    );
}