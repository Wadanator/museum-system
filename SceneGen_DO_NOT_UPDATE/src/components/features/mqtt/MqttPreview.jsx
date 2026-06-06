import React from 'react';

const MqttPreview = ({ action, globalPrefix }) => {
  const hasValidTopic = action.topic && action.topic.includes('/') && action.topic.split('/')[1];
  
  return (
    <div className={`p-3 rounded border ${
      hasValidTopic
        ? 'bg-gray-800 border-gray-600' 
        : 'bg-red-900 border-red-600'
    }`}>
      <div className="text-xs text-gray-400 mb-1"> Náhľad MQTT:</div>
      <div className="text-sm">
        <span className="text-blue-400">Topic:</span> 
        <span className="text-white ml-2 font-mono">{action.topic || '(žiadny)'}</span>
      </div>
      <div className="text-sm mt-1">
        <span className="text-green-400">Message:</span> 
        <span className="text-white ml-2 font-mono">{action.message || '(žiadna)'}</span>
      </div>
      {!hasValidTopic && (
        <div className="text-xs text-red-400 mt-2 font-semibold">
          [WARN] CHYBA: Vyber zariadenie! Topic musí byť napr. "{globalPrefix}/motor1"
        </div>
      )}
    </div>
  );
};

export default MqttPreview;