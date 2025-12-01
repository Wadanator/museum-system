import React from 'react';

const CustomTopicEditor = ({ action, onChange, customTopic, setCustomTopic, globalPrefix }) => {
  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Vlastný MQTT Topic
        </label>
        <input
          type="text"
          value={customTopic}
          onChange={(e) => {
            setCustomTopic(e.target.value);
            onChange({ ...action, topic: e.target.value });
          }}
          className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-blue-500"
          placeholder={`${globalPrefix}/custom_device`}
        />
        <div className="text-xs text-gray-500 mt-1">
          💡 Zadaj ľubovoľný topic, napr. {globalPrefix}/my_device
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Message
        </label>
        <input
          type="text"
          value={action.message || ''}
          onChange={(e) => onChange({ ...action, message: e.target.value })}
          className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-blue-500"
          placeholder="Tvoja správa"
        />
      </div>

      {/* Preview */}
      <div className="bg-gray-800 p-3 rounded border border-blue-600">
        <div className="text-xs text-gray-400 mb-1">📡 Náhľad MQTT:</div>
        <div className="text-sm">
          <span className="text-blue-400">Topic:</span> 
          <span className="text-white ml-2 font-mono">{action.topic || '(žiadny)'}</span>
        </div>
        <div className="text-sm mt-1">
          <span className="text-green-400">Message:</span> 
          <span className="text-white ml-2 font-mono">{action.message || '(žiadna)'}</span>
        </div>
      </div>
    </div>
  );
};

export default CustomTopicEditor;