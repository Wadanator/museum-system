import React, { useState } from 'react';
import PresetDeviceEditor from './PresetDeviceEditor';
import CustomTopicEditor from './CustomTopicEditor';

/**
 * MqttCommandEditor Component
 * Main wrapper with mode switching
 */
const MqttCommandEditor = ({ action, onChange, globalPrefix }) => {
  // Parse current topic to check if it's custom
  const parseCurrentTopic = () => {
    const parts = action.topic?.split('/') || ['', ''];
    return parts[1] || '';
  };

  const currentDevice = parseCurrentTopic();
  const isCustomTopic = action.topic && !['motor1', 'motor2', 'light', 'steam', 'smoke', 'button1_led', 'button2_led', 'audio', 'video'].includes(currentDevice);
  
  const [customMode, setCustomMode] = useState(isCustomTopic);
  const [customTopic, setCustomTopic] = useState(action.topic || '');

  return (
    <div className="space-y-3">
      {/* Mode Switcher */}
      <div className="flex gap-2 mb-3">
        <button
          type="button"
          onClick={() => setCustomMode(false)}
          className={`flex-1 px-3 py-2 rounded text-sm font-semibold transition ${
            !customMode
              ? 'bg-blue-600 text-white'
              : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
          }`}
        >
          📋 Predvolené Zariadenia
        </button>
        <button
          type="button"
          onClick={() => {
            setCustomMode(true);
            setCustomTopic(action.topic || `${globalPrefix}/`);
          }}
          className={`flex-1 px-3 py-2 rounded text-sm font-semibold transition ${
            customMode
              ? 'bg-blue-600 text-white'
              : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
          }`}
        >
          ✏️ Vlastný Topic
        </button>
      </div>

      {/* Render appropriate editor */}
      {customMode ? (
        <CustomTopicEditor
          action={action}
          onChange={onChange}
          customTopic={customTopic}
          setCustomTopic={setCustomTopic}
          globalPrefix={globalPrefix}
        />
      ) : (
        <PresetDeviceEditor
          action={action}
          onChange={onChange}
          globalPrefix={globalPrefix}
        />
      )}
    </div>
  );
};

export default MqttCommandEditor;