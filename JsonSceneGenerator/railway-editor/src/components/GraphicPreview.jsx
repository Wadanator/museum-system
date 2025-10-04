import React, { useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  Handle,
  Position,
  useReactFlow,
  Panel,
} from 'reactflow';
import dagre from 'dagre';

import 'reactflow/dist/style.css';

const StateNodeContent = ({ data }) => {
  const { state, initialState } = data;
  const [expanded, setExpanded] = useState(false);
  const isInitial = state.name === initialState;

  const countActions = (actions) => actions?.length || 0;
  const countTimeline = (timeline) => timeline?.length || 0;

  return (
    <div
      className={`bg-gray-700 rounded-lg p-4 border-2 transition-all w-[380px] cursor-pointer hover:border-blue-500 ${
        isInitial ? 'border-yellow-500' : 'border-gray-600'
      }`}
      onClick={() => setExpanded(!expanded)}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-500" />
      <Handle type="source" position={Position.Bottom} className="!bg-gray-500" />

      {isInitial && (
        <div className="absolute -top-3 -left-3 bg-yellow-500 text-black px-2 py-1 rounded font-bold text-xs">
          ⭐ START
        </div>
      )}
      <h3 className="text-xl font-bold text-white mb-2">{state.name}</h3>
      {state.description && (
        <p className="text-sm text-gray-400 mb-3 -mt-1">{state.description}</p>
      )}

      <div className="grid grid-cols-4 gap-2">
        <div className="bg-green-900 border border-green-600 rounded p-2 text-center">
          <div className="text-xs text-green-300 font-bold">onEnter</div>
          <div className="text-lg text-white font-bold">{countActions(state.onEnter)}</div>
        </div>
        <div className="bg-blue-900 border border-blue-600 rounded p-2 text-center">
          <div className="text-xs text-blue-300 font-bold">Timeline</div>
          <div className="text-lg text-white font-bold">{countTimeline(state.timeline)}</div>
        </div>
        <div className="bg-orange-900 border border-orange-600 rounded p-2 text-center">
          <div className="text-xs text-orange-300 font-bold">onExit</div>
          <div className="text-lg text-white font-bold">{countActions(state.onExit)}</div>
        </div>
        <div className="bg-purple-900 border border-purple-600 rounded p-2 text-center">
          <div className="text-xs text-purple-300 font-bold">Exits</div>
          <div className="text-lg text-white font-bold">{state.transitions?.length || 0}</div>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-600 space-y-2 text-sm font-mono">
          {state.onEnter?.length > 0 && (
            <div className="bg-green-900 p-2 rounded">
              <div className="font-bold text-green-300 mb-1">onEnter:</div>
              {state.onEnter.map((action, idx) => (
                <div key={idx} className="text-green-200 ml-2 truncate">
                  • {action.topic} → {action.message}
                </div>
              ))}
            </div>
          )}
          {state.timeline?.length > 0 && (
            <div className="bg-blue-900 p-2 rounded">
              <div className="font-bold text-blue-300 mb-1">Timeline:</div>
              {state.timeline.map((item, idx) => (
                <div key={idx} className="text-blue-200 ml-2 truncate">
                  • @{item.at}s: {item.topic} → {item.message}
                </div>
              ))}
            </div>
          )}
          {state.onExit?.length > 0 && (
            <div className="bg-orange-900 p-2 rounded">
              <div className="font-bold text-orange-300 mb-1">onExit:</div>
              {state.onExit.map((action, idx) => (
                <div key={idx} className="text-orange-200 ml-2 truncate">
                  • {action.topic} → {action.message}
                </div>
              ))}
            </div>
          )}
          {state.transitions?.length > 0 && (
            <div className="bg-purple-900 p-2 rounded">
              <div className="font-bold text-purple-300 mb-1">Transitions:</div>
              {state.transitions.map((trans, idx) => (
                <div key={idx} className="text-purple-200 ml-2 truncate">
                  • {trans.type}: {trans.target ? `'${trans.target}' ` : ''}→ <span className="font-bold">{trans.goto}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  const isHorizontal = direction === 'LR';
  const nodeWidth = 380;
  const nodeHeight = 150; // Estimate height for non-expanded nodes; adjust if needed

  nodes.forEach((node) => {
    const width = node.id === 'END' ? 150 : nodeWidth;
    const height = node.id === 'END' ? 50 : nodeHeight;
    dagreGraph.setNode(node.id, { width, height });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;
    node.position = {
      x: nodeWithPosition.x - nodeWithPosition.width / 2 + Math.random() / 1000,
      y: nodeWithPosition.y - nodeWithPosition.height / 2,
    };
    return node;
  });

  return { nodes, edges };
};

const GraphicPreviewContent = ({ states, initialState, globalEvents }) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const nodeTypes = useMemo(() => ({ stateNode: StateNodeContent }), []);

  useEffect(() => {
    // Fix: states is an array, not object. Use state.name as id
    const statesArray = states.map((state) => ({
      ...state,
      id: state.name,
    }));

    const existingNodeIds = new Set(statesArray.map((s) => s.id));

    const initialNodes = statesArray.map((state) => ({
      id: state.id,
      type: 'stateNode',
      data: { state, initialState },
      position: { x: 0, y: 0 },
    }));

    const initialEdges = [];
    statesArray.forEach((state) => {
      (state.transitions || []).forEach((t, index) => {
        if (!t.goto || (!existingNodeIds.has(t.goto) && t.goto !== 'END')) {
          return;
        }

        const edgeId = `e-${state.id}-${t.goto}-${index}`;
        let label = t.type;
        if (t.type === 'timeout') label = `Timeout: ${t.delay}s`;
        if (t.type === 'mqttMessage') label = `MQTT: ${t.topic} (${t.message})`;
        if (t.type === 'audioEnd') label = `🎵 End: ${t.target}`;
        if (t.type === 'videoEnd') label = `🎬 End: ${t.target}`;

        initialEdges.push({
          id: edgeId,
          source: state.id,
          target: t.goto,
          label,
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#a855f7', strokeWidth: 2 },
          labelBgStyle: { fill: '#1f2937', fillOpacity: 0.8 },
          labelStyle: { fill: '#d1d5db', fontSize: 12, fontWeight: 'bold' },
        });
      });
    });

    // Add END node if referenced
    if (initialEdges.some((e) => e.target === 'END')) {
      initialNodes.push({
        id: 'END',
        data: { label: '🏁 END' },
        position: { x: 0, y: 0 },
        style: {
          background: '#be123c',
          color: 'white',
          width: 150,
          height: 50,
          border: 'none',
          borderRadius: '50px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
        },
      });
    }

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(initialNodes, initialEdges, 'TB'); // Use 'TB' for top-to-bottom with branching

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    setTimeout(() => fitView({ padding: 0.2, includeHiddenNodes: true }), 0);
  }, [states, initialState, setNodes, setEdges, fitView]);

  return (
    <div className="bg-gray-800 rounded-lg p-6" style={{ height: '1000px' }}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">🗺️ State Machine Flow</h2>
      </div>

      {globalEvents && globalEvents.length > 0 && (
        <div className="bg-yellow-900 border-2 border-yellow-600 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-bold text-yellow-400 mb-2">🚨 Global Events</h3>
          <div className="space-y-1 text-sm">
            {globalEvents.map((event, idx) => (
              <div key={idx} className="text-yellow-200">
                {event.type === 'mqttMessage' && (
                  <>📡 {event.topic}: {event.message} → <span className="font-bold">{event.goto}</span></>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        className="bg-gray-900 rounded"
      >
        <Controls className="react-flow__controls-custom" />
        <Background />
        <Panel position="bottom-left">
          <div className="bg-gray-700 p-2 rounded text-xs text-gray-300">
            Click on a state to see details.
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

const GraphicPreview = (props) => (
  <ReactFlowProvider>
    <GraphicPreviewContent {...props} />
  </ReactFlowProvider>
);

export default GraphicPreview;