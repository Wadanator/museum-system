import React, { useState, useEffect } from 'react';
import { MQTT_DEVICES } from '../../../utils/constants';
import MotorControls from './MotorControls';
import SimpleDeviceControls from './SimpleDeviceControls';
import AudioControls from './AudioControls';
import VideoControls from './VideoControls';
import MqttPreview from './MqttPreview';

const PresetDeviceEditor = ({ action, onChange, globalPrefix }) => {
  const parseCurrentTopic = () => {
    // Ak je action.topic prázdny (audio/video), vrátime podľa typu akcie ak existuje v zozname
    // Ale primárne sa snažíme parsovať topic pre MQTT zariadenia
    if (action.action === 'audio') return 'audio';
    if (action.action === 'video') return 'video';
    
    // Pre MQTT zariadenia hľadáme suffix
    const parts = action.topic?.split('/') || [];
    // Skúsime nájsť zhodu v MQTT_DEVICES podľa suffixu
    // Toto je jednoduchý check, pre zložitejšie suffixy (napr. light/fire) by to chcelo robustnejšie hľadanie,
    // ale pre editor stačí, ak user vyberie znovu zo zoznamu.
    // Pre základnú inicializáciu skúsime nájsť kľúč, ktorého topicSuffix sedí.
    const suffix = action.topic ? action.topic.replace(`${globalPrefix}/`, '') : '';
    const foundKey = Object.keys(MQTT_DEVICES).find(key => MQTT_DEVICES[key].topicSuffix === suffix);
    return foundKey || '';
  };

  const [selectedDevice, setSelectedDevice] = useState(parseCurrentTopic());

  // Update topicu pri zmene prefixu (len pre MQTT)
  useEffect(() => {
    if (selectedDevice && MQTT_DEVICES[selectedDevice]) {
       const deviceInfo = MQTT_DEVICES[selectedDevice];
       if (deviceInfo.type !== 'audio' && deviceInfo.type !== 'video') {
           const newTopic = `${globalPrefix}/${deviceInfo.topicSuffix}`;
           if (action.topic !== newTopic) {
               onChange({ ...action, topic: newTopic });
           }
       }
    }
  }, [globalPrefix]);

  const handleDeviceChange = (deviceKey) => {
    setSelectedDevice(deviceKey);
    const deviceInfo = MQTT_DEVICES[deviceKey];
    
    if (!deviceInfo) return;

    // 1. Zisti správny typ akcie pre JSON export
    let newActionType = 'mqtt'; // default
    if (deviceInfo.type === 'audio') newActionType = 'audio';
    if (deviceInfo.type === 'video') newActionType = 'video';

    // 2. Vyskladaj Topic (Audio/Video ho nemajú)
    const newTopic = (newActionType === 'mqtt') 
        ? `${globalPrefix}/${deviceInfo.topicSuffix}`
        : ''; 

    // 3. Priprav update objekt
    const updatedAction = { 
        ...action, 
        action: newActionType, 
        topic: newTopic 
    };
    
    // 4. Nastav predvolenú správu
    if (deviceInfo.type === 'motor') {
      const speed = deviceInfo.defaultSpeed || 50;
      // Default: Rýchlosť, Smer L, Rampa 0
      onChange({ ...updatedAction, message: `ON:${speed}:L:0` });
    } else if (deviceInfo.type === 'simple') {
      onChange({ ...updatedAction, message: 'ON' });
    } else {
      // Pre Audio/Video správu vyčistíme (alebo necháme prázdnu), nech si ju user nastaví cez UI
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
      {/* Zobrazujeme Preview len pre MQTT zariadenia (Audio/Video ho nepotrebujú) */}
      {selectedDevice && deviceInfo?.type !== 'audio' && deviceInfo?.type !== 'video' ? (
        <MqttPreview action={action} globalPrefix={globalPrefix} />
      ) : null}

      {!selectedDevice && (
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