import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { TRANSITION_TYPES } from '../../../utils/constants';
import { createEmptyTransition } from '../../../utils/generators';

// Button values common in the museum system (RPI/ESP32 compatibility)
const BUTTON_NUMBERS = ['1', '2', '3', '4', '5', '6', '7', '8'];
const BUTTON_MESSAGES = ['PRESSED', 'RELEASED', 'HELD'];

/**
 * TransitionEditor Component
 * Manages state transitions (timeout, mqttMessage, audioEnd, videoEnd, buttonPress)
 */
const TransitionEditor = ({ transitions, onChange, states, globalPrefix }) => {
  const addTransition = () => {
    // Set default transition to buttonPress for better UX in a museum context
    const newTransition = { 
        ...createEmptyTransition(), 
        type: TRANSITION_TYPES.BUTTON_PRESS,
        // Set defaults for buttonPress to avoid empty fields immediately
        topic: `${globalPrefix}/button1`,
        message: BUTTON_MESSAGES[0] 
    };
    onChange([...transitions, newTransition]);
  };

  const updateTransition = (index, updates) => {
    const newTransitions = [...transitions];
    newTransitions[index] = { ...newTransitions[index], ...updates };
    onChange(newTransitions);
  };

  const deleteTransition = (index) => {
    onChange(transitions.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <h4 className="font-semibold text-purple-400">Transitions</h4>
        <button
          onClick={addTransition}
          className="px-2 py-1 bg-purple-600 hover:bg-purple-700 rounded text-sm flex items-center gap-1 transition"
          title="Add transition"
        >
          <Plus size={14} /> Add
        </button>
      </div>

      {transitions.map((trans, index) => {
        // Helper logic to auto-select button number if the topic matches the pattern
        const isButtonPress = trans.type === TRANSITION_TYPES.BUTTON_PRESS;
        const buttonPrefix = `${globalPrefix}/button`;
        const buttonSuffix =
          trans.topic && trans.topic.startsWith(buttonPrefix)
            ? trans.topic.slice(buttonPrefix.length)
            : '';
        const currentButtonNumber = isButtonPress && /^(\d+)$/.test(buttonSuffix) ? buttonSuffix : '';

        return (
          <div
            key={trans.id || index}
            className="bg-gray-700 p-3 rounded border border-gray-600"
          >
            <div className="space-y-2">
              {/* Transition Type Selector */}
              <div className="grid grid-cols-12 gap-2 items-center">
                <select
                  value={trans.type}
                  onChange={(e) => {
                    const newType = e.target.value;
                    const updates = { type: newType };
                    
                    // Reset or set defaults when changing type
                    if (newType === TRANSITION_TYPES.TIMEOUT) {
                      updates.delay = trans.delay || 1.0;
                    } else if (newType === TRANSITION_TYPES.BUTTON_PRESS) {
                      updates.topic = trans.topic || `${globalPrefix}/button1`;
                      updates.message = trans.message || BUTTON_MESSAGES[0];
                    } else if (newType === TRANSITION_TYPES.AUDIO_END || newType === TRANSITION_TYPES.VIDEO_END) {
                      updates.target = trans.target || '';
                    } else if (newType === TRANSITION_TYPES.MQTT_MESSAGE) {
                      updates.topic = trans.topic || '';
                      updates.message = trans.message || '';
                    }
                    
                    updateTransition(index, updates);
                  }}
                  className="col-span-11 px-2 py-1 bg-gray-600 rounded text-sm"
                >
                  <option value={TRANSITION_TYPES.TIMEOUT}>⏱️ Timeout</option>
                  <option value={TRANSITION_TYPES.BUTTON_PRESS}>🔘 Button Press</option>
                  <option value={TRANSITION_TYPES.MQTT_MESSAGE}>📡 Generic MQTT Message</option>
                  <option value={TRANSITION_TYPES.AUDIO_END}>🎵 Audio End</option>
                  <option value={TRANSITION_TYPES.VIDEO_END}>🎬 Video End</option>
                </select>

                {/* Delete Button */}
                <button
                  onClick={() => deleteTransition(index)}
                  className="col-span-1 p-1 bg-red-600 hover:bg-red-700 rounded transition"
                  title="Delete transition"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              {/* Conditional Fields based on Transition Type */}

              {/* Timeout Fields */}
              {trans.type === TRANSITION_TYPES.TIMEOUT && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Delay (seconds)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={trans.delay}
                      onChange={(e) =>
                        updateTransition(index, { delay: parseFloat(e.target.value) || 0 })
                      }
                      className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                      placeholder="1.0"
                    />
                  </div>
                </div>
              )}
              
              {/* Button Press Fields (New Dedicated UI) */}
              {trans.type === TRANSITION_TYPES.BUTTON_PRESS && (
                <div className="bg-blue-900 p-3 rounded border border-blue-600 space-y-2">
                  <h5 className="text-xs text-blue-100 font-semibold">
                    🔘 Button Press Configuration
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {/* Button Selector */}
                    <div>
                      <label className="block text-[11px] text-blue-100 mb-1">
                        Button
                      </label>
                      <select
                        value={currentButtonNumber}
                        onChange={(e) => {
                          const selected = e.target.value;
                          updateTransition(index, {
                            topic: selected ? `${globalPrefix}/button${selected}` : '',
                            message: trans.message || BUTTON_MESSAGES[0] // Preserve message or set default
                          });
                        }}
                        className="w-full px-2 py-1 bg-blue-950/80 border border-blue-700 rounded text-xs"
                      >
                        <option value="">-- select button --</option>
                        {BUTTON_NUMBERS.map((num) => (
                          <option key={`btn-${num}`} value={num}>
                            Button {num}
                          </option>
                        ))}
                      </select>
                    </div>
                    {/* Message Selector */}
                    <div>
                      <label className="block text-[11px] text-blue-100 mb-1">
                        Message State (PRESS/RELEASE/HOLD)
                      </label>
                      <select
                        value={trans.message || BUTTON_MESSAGES[0]}
                        onChange={(e) =>
                          updateTransition(index, {
                            message: e.target.value || BUTTON_MESSAGES[0],
                            topic: currentButtonNumber
                              ? `${globalPrefix}/button${currentButtonNumber}`
                              : trans.topic // Preserve topic if no button selected
                          })
                        }
                        className="w-full px-2 py-1 bg-blue-950/80 border border-blue-700 rounded text-xs"
                      >
                        {BUTTON_MESSAGES.map((msg) => (
                          <option key={`msg-${msg}`} value={msg}>
                            {msg}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <p className="text-[11px] text-blue-200">
                    💡 Topic is automatically set to <code className="font-mono">{`${globalPrefix}/buttonX`}</code>.
                  </p>
                </div>
              )}

              {/* Generic MQTT Message Fields */}
              {trans.type === TRANSITION_TYPES.MQTT_MESSAGE && (
                <div className="space-y-2">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Topic
                    </label>
                    <input
                      type="text"
                      value={trans.topic || ''}
                      onChange={(e) => updateTransition(index, { topic: e.target.value })}
                      className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                      placeholder={`${globalPrefix}/sensor/status`}
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      💡 e.g., {globalPrefix}/sensor/status, {globalPrefix}/device/feedback
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Message</label>
                    <input
                      type="text"
                      value={trans.message || ''}
                      onChange={(e) => updateTransition(index, { message: e.target.value })}
                      className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                      placeholder="TRIGGERED"
                    />
                    <div className="text-xs text-gray-500 mt-1">
                      💡 The transition occurs when the topic receives this exact message.
                    </div>
                  </div>
                </div>
              )}

              {/* Audio End Fields */}
              {trans.type === TRANSITION_TYPES.AUDIO_END && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Target Audio File (which file must finish playing)
                  </label>
                  <input
                    type="text"
                    value={trans.target || ''}
                    onChange={(e) => updateTransition(index, { target: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder="intro.mp3"
                  />
                  <div className="text-xs text-gray-500 mt-1">
                    💡 The transition triggers when this audio file finishes.
                  </div>
                </div>
              )}

              {/* Video End Fields */}
              {trans.type === TRANSITION_TYPES.VIDEO_END && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Target Video File (which file must finish playing)
                  </label>
                  <input
                    type="text"
                    value={trans.target || ''}
                    onChange={(e) => updateTransition(index, { target: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder="scary.mp4"
                  />
                  <div className="text-xs text-gray-500 mt-1">
                    💡 The transition triggers when this video finishes.
                  </div>
                </div>
              )}

              {/* Go To State Selector (Common to all types) */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">Goto (Target State)</label>
                <select
                  value={trans.goto}
                  onChange={(e) => updateTransition(index, { goto: e.target.value })}
                  className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                >
                  <option value="">Go to...</option>
                  {states.map((state) => (
                    <option key={state.id} value={state.name}>
                      {state.name}
                    </option>
                  ))}
                  <option value="END">END</option>
                </select>
              </div>
            </div>
          </div>
        );
      })}

      {transitions.length === 0 && (
        <p className="text-sm text-gray-400 italic py-2">No transitions defined</p>
      )}
    </div>
  );
};

export default TransitionEditor;