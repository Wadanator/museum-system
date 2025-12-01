import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  Background,
  Position,
  useReactFlow,
  Panel,
  addEdge,
} from 'reactflow';
import dagre from 'dagre';
import SceneNode from './SceneNode';

import 'reactflow/dist/style.css';

const initialNodePositions = {};

// [POMOCNÁ FUNKCIA DAGRE - BEZ ZMENY]
const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  const isHorizontal = direction === 'LR';
  const nodeWidth = 380;
  const nodeHeight = 150; 

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


// [FUNKCIA PRE GENERÁCIU UZLOV A HRÁN - IMPLEMENTÁCIA OFFSETU]
const getElementsFromStates = (states, initialState, nodePositions) => {
  const statesArray = states.map((state) => ({
    ...state,
    id: state.id,
  }));

  const existingNodeNames = new Map(statesArray.map(s => [s.name, s.id]));

  const initialNodes = statesArray.map((state) => ({
    id: state.id,
    type: 'sceneNode',
    data: { 
      state, 
      initialState: initialState === state.name 
    },
    position: nodePositions[state.id] || { x: 0, y: 0 }, 
  }));

  const initialEdges = [];
  
  // Krok 1: Zoskupenie tranzícií
  const groupedTransitions = {}; 

  statesArray.forEach((state) => {
    (state.transitions || []).forEach((t, index) => {
      const targetStateId = existingNodeNames.get(t.goto);
      
      if (!t.goto || (!targetStateId && t.goto !== 'END')) {
        return;
      }
      
      const targetId = targetStateId || 'END';
      const key = `${state.id}->${targetId}`;
      
      if (!groupedTransitions[key]) {
          groupedTransitions[key] = [];
      }
      
      let label = t.type;
      if (t.type === 'timeout') label = `Timeout: ${t.delay}s`;
      if (t.type === 'mqttMessage') label = `MQTT: ${t.topic} (${t.message})`;
      if (t.type === 'audioEnd') label = `🎵 End: ${t.target}`;
      if (t.type === 'videoEnd') label = `🎬 End: ${t.target}`;

      groupedTransitions[key].push({
          id: `e-${state.id}-${targetId}-${groupedTransitions[key].length}`, 
          source: state.id,
          target: targetId,
          label,
          transitionData: t, 
      });
    });
  });

  // Krok 2: Aplikácia offsetu pre labely
  Object.values(groupedTransitions).forEach(transitions => {
      const isMultiple = transitions.length > 1;
      const step = 20; // Vertikálny posun v pixeloch
      // Vypočítame offset pre centrovanie labelov
      const centerOffset = ((transitions.length - 1) / 2) * step; 
      
      transitions.forEach((edgeData, index) => {
          // Posun labelu, aby sa neprekrývali
          const labelOffset = (index * step) - centerOffset;
          
          initialEdges.push({
              id: edgeData.id,
              source: edgeData.source,
              target: edgeData.target,
              label: edgeData.label,
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#a855f7', strokeWidth: 2 },
              labelBgStyle: { fill: '#1f2937', fillOpacity: 0.8 },
              labelStyle: { 
                  fill: '#d1d5db', 
                  fontSize: 12, 
                  fontWeight: 'bold',
                  // KĽÚČOVÁ ZMENA: Aplikácia transform posunu
                  transform: isMultiple ? `translate(0px, ${labelOffset}px)` : 'none' 
              },
              data: { 
                  transitionId: edgeData.transitionData.id,
                  transitionType: edgeData.transitionData.type
              },
          });
      });
  });
  
  // Pridanie uzla 'END'
  if (initialEdges.some((e) => e.target === 'END')) {
    initialNodes.push({
      id: 'END',
      data: { label: '🏁 END' },
      position: nodePositions['END'] || { x: 100, y: 50 },
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
      draggable: false, 
      selectable: false,
    });
  }

  return { nodes: initialNodes, edges: initialEdges };
};


const GraphicPreviewContent = ({ states, initialState, globalEvents, onAddState, onUpdateState, onEdgesDelete, onNodeClick, onNodeDoubleClick }) => {
  const { fitView, project } = useReactFlow();
  const [nodePositions, setNodePositions] = useState(initialNodePositions); 

  const { nodes: elementsNodes, edges: elementsEdges } = useMemo(() => {
    return getElementsFromStates(states, initialState, nodePositions);
  }, [states, initialState, nodePositions]);
  
  const [nodes, setNodes, onNodesChange] = useNodesState(elementsNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(elementsEdges);
  
  const firstRender = useRef(true);
  
  // [DAGRE LAYOUT]
  const dagreLayout = useCallback((nodesToLayout, edgesToLayout) => {
    const nodesToLayoutCopy = nodesToLayout.map(n => ({...n}));
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(nodesToLayoutCopy, edgesToLayout, 'TB');
    
    const newPositions = layoutedNodes.reduce((acc, node) => {
        acc[node.id] = node.position;
        return acc;
    }, {});
    setNodePositions(newPositions);
    
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    setTimeout(() => fitView({ padding: 0.2, includeHiddenNodes: true }), 0);
  }, [setNodes, setEdges, fitView]);
  
  // [SYNCHRONIZÁCIA DÁT A AUTO-LAYOUT PRI ŠTARTE]
  useEffect(() => {
    setNodes(elementsNodes);
    setEdges(elementsEdges);

    if (firstRender.current && elementsNodes.length > 0) {
        dagreLayout(elementsNodes, elementsEdges); 
        firstRender.current = false;
    }
  }, [elementsNodes, elementsEdges, setNodes, setEdges, dagreLayout]);
  
  
  const handleNodeDataUpdate = useCallback((stateId, updates) => {
    onUpdateState(stateId, updates);
  }, [onUpdateState]);
  
  const nodeTypes = useMemo(() => ({ 
    sceneNode: (props) => (
      <SceneNode 
        {...props} 
        initialState={initialState} 
        updateNodeData={handleNodeDataUpdate} 
      />
    )
  }), [initialState, handleNodeDataUpdate]); 


  // [CLICK HANDLERS]
  const clickTimer = useRef(null);

  const onNodeClickHandler = useCallback((event, node) => {
      if (event.target.tagName === 'INPUT') return;

      if (clickTimer.current) {
          clearTimeout(clickTimer.current);
          clickTimer.current = null;
          if (onNodeDoubleClick) {
              onNodeDoubleClick(event, node);
          }
      } else {
          clickTimer.current = setTimeout(() => {
              clickTimer.current = null;
              if (onNodeClick) {
                  onNodeClick(event, node);
              }
          }, 250); 
      }
  }, [onNodeClick, onNodeDoubleClick]);
  
  
  const onPaneDoubleClick = useCallback((event) => {
    const position = project({ x: event.clientX, y: event.clientY });
    onAddState({ position }); 
  }, [onAddState, project]);


  const onNodesChangeWithPositionSave = useCallback((changes) => {
    onNodesChange(changes);
    
    changes.forEach(change => {
      if (change.type === 'position' && change.position) {
        setNodePositions(prevPos => ({
          ...prevPos,
          [change.id]: change.position
        }));
      }
    });
  }, [onNodesChange]);


  const onConnect = useCallback((params) => {
    const sourceState = states.find(s => s.id === params.source);
    
    if (sourceState) {
        const targetNode = nodes.find(n => n.id === params.target);
        const targetStateName = targetNode?.data?.state?.name || 'END'; 
        
        const newTransition = {
            id: `${sourceState.id}-${targetStateName}-${sourceState.transitions.length}`, 
            type: 'timeout',
            delay: 1.0, 
            goto: targetStateName
        };
        
        const newStateTransitions = [...sourceState.transitions, newTransition];

        onUpdateState(sourceState.id, { transitions: newStateTransitions }); 
    }
  }, [nodes, states, onUpdateState]);
  
  const onEdgesDeleteHandler = useCallback((edgesToDelete) => {
      onEdgesDelete(edgesToDelete);
  }, [onEdgesDelete]);
  

  return (
    <div className="bg-gray-800 rounded-lg p-6" style={{ height: '1000px' }}>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">🗺️ State Machine Flow Editor</h2>
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

      <div style={{ height: '800px', border: '1px solid #374151' }} className="rounded-lg">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChangeWithPositionSave}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onEdgesDelete={onEdgesDeleteHandler}
          onNodeClick={onNodeClickHandler}
          onPaneDoubleClick={onPaneDoubleClick}
          nodeTypes={nodeTypes}
          fitView
          className="bg-gray-900 rounded"
          proOptions={{ hideAttribution: true }}
        >
          <Background />
          <Panel position="top-right">
              <button 
                  onClick={() => dagreLayout(nodes, edges)} 
                  className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 rounded text-sm text-white transition"
              >
                  Auto-Layout
              </button>
          </Panel>
          <Panel position="bottom-left">
            <div className="bg-gray-700 p-2 rounded text-xs text-gray-300">
              Dvojklik na prázdnu plochu pre pridanie stavu. **Dvojklik na stav** pre prechod do Editora. Potiahnutím z uzla vytvoríte tranzíciu.
            </div>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  );
};

const GraphicPreview = (props) => (
  <ReactFlowProvider>
    <GraphicPreviewContent {...props} />
  </ReactFlowProvider>
);

export default GraphicPreview;