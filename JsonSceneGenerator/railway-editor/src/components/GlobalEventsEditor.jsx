import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { TRANSITION_TYPES } from '../utils/constants';

/**
 * GlobalEventsEditor Component
 * Manages global events (emergency stops, etc.)
 */
const GlobalEventsEditor = ({ globalEvents, onChange, states, globalPrefix }) => {
  const addGlobalEvent = () => {
    const newEvent = {
      id: `ge_${Date.now()}`,
      type: TRANSITION_TYPES.MQTT_MESSAGE,
      topic: `${globalPrefix}/emergency`,
      message: 'STOP',
      goto: 'END'
    };
    onChange([...globalEvents, newEvent]);
  };

  const updateGlobalEvent = (index, updates) => {
    const newEvents = [...globalEvents];
    newEvents[index] = { ...newEvents[index], ...updates };
    onChange(newEvents);
  };

  const deleteGlobalEvent = (index) => {
    onChange(globalEvents.filter((_, i) => i !== index));
  };

  return (
    <div className="mt-6">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-bold text-yellow-400">🚨 Global Events</h3>
        <button
          onClick={addGlobalEvent}
          className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-sm flex items-center gap-1 transition"
          title="Add global event"
        >
          <Plus size={14} /> Add Global Event
        </button>
      </div>

      <div className="text-xs text-gray-400 mb-3">
        Global events sa spúšťajú kedykoľvek, bez ohľadu na aktuálny stav (napr. emergency stop)
      </div>

      {globalEvents.map((event, index) => (
        <div key={event.id || index} className="bg-gray-700 p-3 rounded mb-2 border border-yellow-600">
          <div className="space-y-2">
            {/* Event Type */}
            <div className="grid grid-cols-12 gap-2 items-center">
              <select
                value={event.type}
                onChange={(e) => updateGlobalEvent(index, { type: e.target.value })}
                className="col-span-11 px-2 py-1 bg-gray-600 rounded text-sm"
              >
                <option value={TRANSITION_TYPES.MQTT_MESSAGE}>📡 MQTT Message</option>
              </select>

              {/* Delete Button */}
              <button
                onClick={() => deleteGlobalEvent(index)}
                className="col-span-1 p-1 bg-red-600 hover:bg-red-700 rounded transition"
                title="Delete global event"
              >
                <Trash2 size={16} />
              </button>
            </div>

            {/* MQTT Message Fields */}
            {event.type === TRANSITION_TYPES.MQTT_MESSAGE && (
              <div className="space-y-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Topic
                  </label>
                  <input
                    type="text"
                    value={event.topic || ''}
                    onChange={(e) => updateGlobalEvent(index, { topic: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder={`${globalPrefix}/emergency`}
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Message</label>
                  <input
                    type="text"
                    value={event.message || ''}
                    onChange={(e) => updateGlobalEvent(index, { message: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder="STOP"
                  />
                </div>
              </div>
            )}

            {/* Go To State Selector */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Goto (cieľový stav)</label>
              <select
                value={event.goto}
                onChange={(e) => updateGlobalEvent(index, { goto: e.target.value })}
                className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
              >
                <option value="">Select state...</option>
                {states.map(state => (
                  <option key={state.id} value={state.name}>{state.name}</option>
                ))}
                <option value="END">END</option>
              </select>
            </div>
          </div>
        </div>
      ))}

      {globalEvents.length === 0 && (
        <div className="text-sm text-gray-400 italic py-2 bg-gray-700 p-3 rounded">
          No global events defined. Global events are useful for emergency stops.
        </div>
      )}
    </div>
  );
};

export default GlobalEventsEditor;