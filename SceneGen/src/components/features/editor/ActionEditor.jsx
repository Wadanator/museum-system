import React, { useState } from 'react';
import { Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import MqttCommandEditor from '../mqtt/MqttCommandEditor';

/**
 * ActionEditor Component
 * Edits individual actions (everything is an MQTT command in this system)
 */
const ActionEditor = ({ action, onChange, onDelete, globalPrefix }) => {
  // Auto-expand new actions (if no topic/message is set)
  const isNew = !action.topic && !action.message;
  const [expanded, setExpanded] = useState(isNew);

  return (
    <div className="bg-gray-700 p-3 rounded mb-2 border border-gray-600">
      {/* Compact View */}
      <div className="flex items-center gap-2">
        {/* MQTT Label */}
        <div className="px-3 py-2 bg-blue-600 rounded text-sm font-semibold">
          MQTT
        </div>

        {/* Quick Preview */}
        <div className="flex-1 text-sm text-gray-300 truncate">
          <span className="text-blue-400">{action.topic || '(no topic)'}</span>
          {' → '}
          <span className="text-green-400">{action.message || '(no message)'}</span>
        </div>

        {/* Expand/Collapse Button */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded transition"
          title={expanded ? 'Collapse' : 'Expand'}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {/* Delete Button */}
        <button
          onClick={onDelete}
          className="p-2 bg-red-600 hover:bg-red-700 rounded transition"
          title="Delete action"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {/* Expanded View */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-600">
          <MqttCommandEditor 
            action={action} 
            onChange={onChange}
            globalPrefix={globalPrefix}
          />
        </div>
      )}
    </div>
  );
};

export default ActionEditor;