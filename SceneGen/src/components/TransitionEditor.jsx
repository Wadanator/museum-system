import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { TRANSITION_TYPES } from '../utils/constants';
import { createEmptyTransition } from '../utils/generators';

const BUTTON_NUMBERS = ['1', '2', '3', '4', '5', '6', '7', '8'];
const BUTTON_MESSAGES = ['PRESSED', 'RELEASED', 'HELD'];

/**
 * TransitionEditor Component
 * Manages state transitions (timeout, mqttMessage, audioEnd, videoEnd)
 */
const TransitionEditor = ({ transitions, onChange, states, globalPrefix }) => {
  const addTransition = () => {
    onChange([...transitions, createEmptyTransition()]);
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
        const buttonPrefix = `${globalPrefix}/button`;
        const buttonSuffix =
          trans.topic && trans.topic.startsWith(buttonPrefix)
            ? trans.topic.slice(buttonPrefix.length)
            : '';
        const buttonNumber = /^(\d+)$/.test(buttonSuffix) ? buttonSuffix : '';

        return (
          <div key={trans.id || index} className="bg-gray-700 p-3 rounded border border-gray-600">
            <div className="space-y-2">
            {/* Transition Type */}
            <div className="grid grid-cols-12 gap-2 items-center">
              <select
                value={trans.type}
                onChange={(e) => updateTransition(index, { type: e.target.value })}
                className="col-span-11 px-2 py-1 bg-gray-600 rounded text-sm"
              >
                <option value={TRANSITION_TYPES.TIMEOUT}>⏱️ Timeout - Časový limit</option>
                <option value={TRANSITION_TYPES.MQTT_MESSAGE}>📡 MQTT Message - MQTT správa</option>
                <option value={TRANSITION_TYPES.AUDIO_END}>🎵 Audio End - Koniec audia</option>
                <option value={TRANSITION_TYPES.VIDEO_END}>🎬 Video End - Koniec videa</option>
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

            {/* Timeout Fields */}
            {trans.type === TRANSITION_TYPES.TIMEOUT && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Delay (sekundy)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={trans.delay}
                    onChange={(e) => updateTransition(index, { delay: parseFloat(e.target.value) || 0 })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder="1.0"
                  />
                </div>
              </div>
            )}

            {/* MQTT Message Fields */}
            {trans.type === TRANSITION_TYPES.MQTT_MESSAGE && (
              <div className="space-y-2">
                {/* Button Helper */}
                <div className="bg-blue-900 p-3 rounded border border-blue-600 space-y-2">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <label className="text-xs text-blue-100 font-semibold">
                      🔘 Generátor tlačidla (MQTT topic + message)
                    </label>
                    <span className="text-[10px] uppercase tracking-wide text-blue-200">
                      Raspberry Pi kompatibilné
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[11px] text-blue-100 mb-1">
                        Tlačidlo
                      </label>
                      <select
                        value={buttonNumber}
                        onChange={(e) => {
                          const selected = e.target.value;
                          updateTransition(index, {
                            topic: selected
                              ? `${globalPrefix}/button${selected}`
                              : '',
                            message: trans.message || 'PRESSED'
                          });
                        }}
                        className="w-full px-2 py-1 bg-blue-950/80 border border-blue-700 rounded text-xs"
                      >
                        <option value="">-- vyber --</option>
                        {BUTTON_NUMBERS.map((num) => (
                          <option key={num} value={num}>
                            Button {num}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-blue-100 mb-1">
                        Stav správy
                      </label>
                      <select
                        value={trans.message || BUTTON_MESSAGES[0]}
                        onChange={(e) =>
                          updateTransition(index, {
                            message: e.target.value || 'PRESSED',
                            topic: buttonNumber
                              ? `${globalPrefix}/button${buttonNumber}`
                              : trans.topic
                          })
                        }
                        className="w-full px-2 py-1 bg-blue-950/80 border border-blue-700 rounded text-xs"
                      >
                        {BUTTON_MESSAGES.map((msg) => (
                          <option key={msg} value={msg}>
                            {msg}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <p className="text-[11px] text-blue-200">
                    💡 Témy sa automaticky doplnia ako <code className="font-mono">{`${globalPrefix}/buttonX`}</code>.
                  </p>
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Topic
                  </label>
                  <input
                    type="text"
                    value={trans.topic || ''}
                    onChange={(e) => updateTransition(index, { topic: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder={`${globalPrefix}/button1`}
                  />
                  <div className="text-xs text-gray-500 mt-1">
                    💡 Pre button: {globalPrefix}/button1, {globalPrefix}/button2, atď.
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Message</label>
                  <input
                    type="text"
                    value={trans.message || ''}
                    onChange={(e) => updateTransition(index, { message: e.target.value })}
                    className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                    placeholder="PRESSED"
                  />
                  <div className="text-xs text-gray-500 mt-1">
                    💡 Pre tlačidlo použi hodnoty ako PRESSED, RELEASED alebo HELD.
                  </div>
                </div>
              </div>
            )}

            {/* Audio End Fields */}
            {trans.type === TRANSITION_TYPES.AUDIO_END && (
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Target Audio File (ktorý súbor musí dohrať)
                </label>
                <input
                  type="text"
                  value={trans.target || ''}
                  onChange={(e) => updateTransition(index, { target: e.target.value })}
                  className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                  placeholder="intro.mp3"
                />
                <div className="text-xs text-gray-500 mt-1">
                  💡 Prechod sa spustí keď sa tento audio súbor dohrá
                </div>
              </div>
            )}

            {/* Video End Fields */}
            {trans.type === TRANSITION_TYPES.VIDEO_END && (
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Target Video File (ktorý súbor musí dohrať)
                </label>
                <input
                  type="text"
                  value={trans.target || ''}
                  onChange={(e) => updateTransition(index, { target: e.target.value })}
                  className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
                  placeholder="scary.mp4"
                />
                <div className="text-xs text-gray-500 mt-1">
                  💡 Prechod sa spustí keď sa toto video dohrá
                </div>
              </div>
            )}

            {/* Go To State Selector */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Goto (cieľový stav)</label>
              <select
                value={trans.goto}
                onChange={(e) => updateTransition(index, { goto: e.target.value })}
                className="w-full px-2 py-1 bg-gray-600 rounded text-sm"
              >
                <option value="">Go to...</option>
                {states.map(state => (
                  <option key={state.id} value={state.name}>{state.name}</option>
                ))}
                <option value="END">END</option>
              </select>
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