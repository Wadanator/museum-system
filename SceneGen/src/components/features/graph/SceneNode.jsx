import React from 'react';
import { Handle, Position } from 'reactflow';

const SceneNode = ({ data, isConnectable, selected, updateNodeData }) => {
    const { state, initialState } = data;
    const [expanded, setExpanded] = React.useState(false);
    const isStartNode = state.name === initialState;

    const handleNameChange = (e) => {
        e.stopPropagation(); 
        const newName = e.target.value;
        updateNodeData(state.id, { name: newName });
    };

    const countActions = (actions) => actions?.length || 0;
    const countTimeline = (timeline) => timeline?.length || 0;

    return (
        <div
            className={`bg-gray-700 rounded-lg p-4 border-2 transition-all w-[380px] hover:border-blue-500 ${
                isStartNode ? 'border-yellow-500' : 'border-gray-600'
            } ${selected ? 'shadow-lg shadow-indigo-500/50' : ''}`}
            onClick={() => setExpanded(!expanded)} 
            onDoubleClick={(e) => e.stopPropagation()}
        >
            <Handle type="target" position={Position.Top} className="!bg-gray-500" isConnectable={isConnectable} />
            <Handle type="source" position={Position.Bottom} className="!bg-gray-500" isConnectable={isConnectable} />

            {isStartNode && (
                <div className="absolute -top-3 -left-3 bg-yellow-500 text-black px-2 py-1 rounded font-bold text-xs">
                    ⭐ START
                </div>
            )}
            
            <div className="mb-2">
                <input
                    type="text"
                    value={state.name}
                    onChange={handleNameChange}
                    className="text-xl font-bold text-white bg-transparent border-b border-gray-500 focus:border-blue-400 outline-none w-full text-center"
                    placeholder="Názov Scény"
                    title="Upraviť Názov Scény (Zmení názov aj v Transition odkazoch)"
                    onClick={(e) => e.stopPropagation()} 
                />
            </div>

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

export default SceneNode;