import React, { useState, useEffect } from 'react';
import { MQTT_DEVICES } from '../../../utils/constants';
import MotorControls from './MotorControls';
import SimpleDeviceControls from './SimpleDeviceControls';
import AudioControls from './AudioControls';
import VideoControls from './VideoControls';
import MqttPreview from './MqttPreview';

const PresetDeviceEditor = ({ action, onChange, globalPrefix }) => {
  const parseCurrentTopic = () => {
    const parts = action.topic?.split('/') || ['', ''];
    return parts[1] || '';
  };

  const [selectedDevice, setSelectedDevice] = useState(parseCurrentTopic());

  const updateTopic = (device) => {
    if (!device) return;
    const newTopic = `${globalPrefix}/${device}`;
    onChange({ ...action, topic: newTopic });
  };

  useEffect(() => {
    if (selectedDevice) {
      updateTopic(selectedDevice);
    }
  }, [globalPrefix]);

  const handleDeviceChange = (device) => {
    setSelectedDevice(device);
    
    const deviceInfo = MQTT_DEVICES[device];
    const newTopic = `${globalPrefix}/${device}`;
    const updatedAction = { ...action, topic: newTopic };
    
    // Reset to defaults based on device type
    if (deviceInfo?.type === 'motor') {
      onChange({ ...updatedAction, message: 'ON:50:L' });
    } else if (deviceInfo?.type === 'simple') {
      onChange({ ...updatedAction, message: 'ON' });
    } else {
      onChange({ ...updatedAction, message: '' });
    }
  };

  const deviceInfo = selectedDevice ? MQTT_DEVICES[selectedDevice] : null;

  return (
    <>
      {/* Device Selector */}
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Zariadenie
        </label>
        <select
          value={selectedDevice}
          onChange={(e) => handleDeviceChange(e.target.value)}
          className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="">-- Vyber zariadenie --</option>
          {Object.entries(MQTT_DEVICES).map(([key, device]) => (
            <option key={key} value={key}>
              {device.label}
            </option>
          ))}
        </select>
      </div>

      {/* Device-specific controls */}
      {deviceInfo?.type === 'motor' && (
        <MotorControls action={action} onChange={onChange} />
      )}

      {deviceInfo?.type === 'simple' && (
        <SimpleDeviceControls 
          action={action} 
          onChange={onChange} 
          commands={deviceInfo.commands}
        />
      )}

      {deviceInfo?.type === 'audio' && (
        <AudioControls action={action} onChange={onChange} />
      )}

      {deviceInfo?.type === 'video' && (
        <VideoControls action={action} onChange={onChange} />
      )}

      {/* Preview or warning */}
      {selectedDevice ? (
        <MqttPreview action={action} globalPrefix={globalPrefix} />
      ) : (
        <div className="bg-yellow-900 p-3 rounded border border-yellow-600">
          <div className="text-sm text-yellow-200">
            ⚠️ Najprv vyber zariadenie
          </div>
        </div>
      )}
    </>
  );
};

export default PresetDeviceEditor;