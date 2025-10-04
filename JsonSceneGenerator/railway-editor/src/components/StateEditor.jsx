import React, { useState } from 'react';
import { Trash2, Plus, ChevronDown, ChevronUp } from 'lucide-react';
import ActionEditor from './ActionEditor';
import TimelineEditor from './TimelineEditor';
import TransitionEditor from './TransitionEditor';
import { createEmptyAction } from '../utils/generators';

/**
 * StateEditor Component
 * Edits a complete state with all its properties
 */
const StateEditor = ({ state, onChange, onDelete, states, globalPrefix }) => {
  const [expanded, setExpanded] = useState(false);

  const updateOnEnter = (actions) => onChange({ ...state, onEnter: actions });
  const updateOnExit = (actions) => onChange({ ...state, onExit: actions });
  const updateTimeline = (timeline) => onChange({ ...state, timeline });
  const updateTransitions = (transitions) => onChange({ ...state, transitions });

  const addAction = (type) => {
    const newAction = createEmptyAction();
    // Automaticky expandni novú akciu nastavením expanded state
    const newActions = [...(state[type] || []), newAction];
    onChange({ ...state, [type]: newActions });
  };

  const updateAction = (type, index, updates) => {
    const actions = [...state[type]];
    actions[index] = { ...actions[index], ...updates };
    onChange({ ...state, [type]: actions });
  };

  const deleteAction = (type, index) => {
    onChange({ ...state, [type]: state[type].filter((_, i) => i !== index) });
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4 border-2 border-gray-700 hover:border-gray-600 transition">
      {/* State Header */}
      <div className="flex justify-between items-center mb-3">
        <div className="flex-1">
          <input
            type="text"
            value={state.name}
            onChange={(e) => onChange({ ...state, name: e.target.value })}
            className="bg-gray-700 px-3 py-2 rounded font-bold text-lg w-full focus:ring-2 focus:ring-blue-500"
            placeholder="State Name"
          />
          <input
            type="text"
            value={state.description}
            onChange={(e) => onChange({ ...state, description: e.target.value })}
            className="bg-gray-700 px-3 py-1 rounded text-sm w-full mt-2 focus:ring-2 focus:ring-blue-500"
            placeholder="Description"
          />
        </div>
        <div className="flex gap-2 ml-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded transition flex items-center gap-2"
            title={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            {expanded ? 'Collapse' : 'Expand'}
          </button>
          <button
            onClick={onDelete}
            className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded transition"
            title="Delete state"
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      {/* State Content (when expanded) */}
      {expanded && (
        <div className="space-y-4 mt-4 pt-4 border-t border-gray-700">
          {/* OnEnter Actions */}
          <div className="bg-gray-750 p-3 rounded">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-green-400">On Enter Actions</h4>
              <button
                onClick={() => addAction('onEnter')}
                className="px-2 py-1 bg-green-600 hover:bg-green-700 rounded text-sm flex items-center gap-1 transition"
                title="Add onEnter action"
              >
                <Plus size={14} /> Add
              </button>
            </div>
            {state.onEnter?.length > 0 ? (
              state.onEnter.map((action, idx) => (
                <ActionEditor
                  key={action.id || idx}
                  action={action}
                  onChange={(updated) => updateAction('onEnter', idx, updated)}
                  onDelete={() => deleteAction('onEnter', idx)}
                  globalPrefix={globalPrefix}
                />
              ))
            ) : (
              <p className="text-sm text-gray-400 italic py-2">No onEnter actions</p>
            )}
          </div>

          {/* Timeline */}
          <div className="bg-gray-750 p-3 rounded">
            <TimelineEditor
              timelineItems={state.timeline || []}
              onChange={updateTimeline}
              globalPrefix={globalPrefix}
            />
          </div>

          {/* OnExit Actions */}
          <div className="bg-gray-750 p-3 rounded">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-orange-400">On Exit Actions</h4>
              <button
                onClick={() => addAction('onExit')}
                className="px-2 py-1 bg-orange-600 hover:bg-orange-700 rounded text-sm flex items-center gap-1 transition"
                title="Add onExit action"
              >
                <Plus size={14} /> Add
              </button>
            </div>
            {state.onExit?.length > 0 ? (
              state.onExit.map((action, idx) => (
                <ActionEditor
                  key={action.id || idx}
                  action={action}
                  onChange={(updated) => updateAction('onExit', idx, updated)}
                  onDelete={() => deleteAction('onExit', idx)}
                  globalPrefix={globalPrefix}
                />
              ))
            ) : (
              <p className="text-sm text-gray-400 italic py-2">No onExit actions</p>
            )}
          </div>

          {/* Transitions */}
          <div className="bg-gray-750 p-3 rounded">
            <TransitionEditor
              transitions={state.transitions || []}
              onChange={updateTransitions}
              states={states}
              globalPrefix={globalPrefix}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default StateEditor;