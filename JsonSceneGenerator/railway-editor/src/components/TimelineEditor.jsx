import React from 'react';
import { Plus } from 'lucide-react';
import ActionEditor from './ActionEditor';
import { createEmptyAction } from '../utils/generators';

/**
 * TimelineEditor Component
 * Manages timeline actions with timestamps
 */
const TimelineEditor = ({ timelineItems, onChange, globalPrefix }) => {
  const addTimelineItem = () => {
    onChange([...timelineItems, { at: 0, ...createEmptyAction() }]);
  };

  const updateTimelineItem = (index, updates) => {
    const newTimeline = [...timelineItems];
    newTimeline[index] = { ...newTimeline[index], ...updates };
    onChange(newTimeline);
  };

  const deleteTimelineItem = (index) => {
    onChange(timelineItems.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <h4 className="font-semibold text-blue-400">Timeline Actions</h4>
        <button
          onClick={addTimelineItem}
          className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm flex items-center gap-1 transition"
          title="Add timeline action"
        >
          <Plus size={14} /> Add
        </button>
      </div>

      {timelineItems.map((item, index) => (
        <div key={item.id || index} className="bg-gray-700 p-3 rounded border border-gray-600">
          <div className="flex gap-2 mb-2 items-center">
            <label className="text-sm text-gray-400">At:</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={item.at}
              onChange={(e) => updateTimelineItem(index, { at: parseFloat(e.target.value) || 0 })}
              className="w-24 px-2 py-1 bg-gray-600 rounded text-sm"
              placeholder="0.0"
            />
            <span className="text-sm text-gray-400">seconds</span>
          </div>
          <ActionEditor
            action={item}
            onChange={(updated) => updateTimelineItem(index, updated)}
            onDelete={() => deleteTimelineItem(index)}
            globalPrefix={globalPrefix}
          />
        </div>
      ))}

      {timelineItems.length === 0 && (
        <p className="text-sm text-gray-400 italic py-2">No timeline actions</p>
      )}
    </div>
  );
};

export default TimelineEditor;