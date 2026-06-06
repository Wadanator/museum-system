import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import ActionEditor from './ActionEditor';
import { createEmptyAction } from '../../../utils/generators';

const TimelineEditor = ({ timeline, onChange, globalPrefix }) => {
  // Fallback ak by náhodou prišlo undefined
  const safeTimeline = timeline || [];

  const addTimelineItem = () => {
    onChange([...safeTimeline, { at: 0, ...createEmptyAction() }]);
  };

  const updateTimelineItem = (index, updates) => {
    const newTimeline = [...safeTimeline];
    newTimeline[index] = { ...newTimeline[index], ...updates };
    onChange(newTimeline);
  };

  const deleteTimelineItem = (index) => {
    onChange(safeTimeline.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <button
          onClick={addTimelineItem}
          className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-xs flex items-center gap-1 transition uppercase font-bold tracking-wider"
          title="Pridať časovanú akciu"
        >
          <Plus size={12} /> Pridať Timeline Akciu
        </button>
      </div>

      {safeTimeline.length === 0 && (
        <p className="text-sm text-gray-500 italic py-2 text-center border border-dashed border-gray-700 rounded">
            Žiadne časované akcie.
        </p>
      )}

      {safeTimeline.map((item, index) => (
        <div key={item.id || index} className="bg-gray-700/50 p-3 rounded border border-gray-600 flex gap-4 items-start">
          
          {/* Časovanie */}
          <div className="flex flex-col items-center gap-1 pt-1">
            <label className="text-[10px] text-gray-400 uppercase font-bold">Čas (s)</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={item.at}
              onChange={(e) => updateTimelineItem(index, { at: parseFloat(e.target.value) || 0 })}
              className="w-16 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-center focus:border-blue-500 outline-none"
              placeholder="0.0"
            />
          </div>

          {/* Akcia */}
          <div className="flex-1 min-w-0">
             <ActionEditor
                action={item}
                onChange={(updated) => updateTimelineItem(index, updated)}
                onDelete={() => deleteTimelineItem(index)}
                globalPrefix={globalPrefix}
             />
          </div>
        </div>
      ))}
    </div>
  );
};

export default TimelineEditor;