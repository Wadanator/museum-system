import React from 'react';

/**
 * Header Component
 * Scene metadata editor and central scene selection (sceneId, description, version, initialState)
 */
const Header = ({ sceneId, description, version, initialState, globalPrefix, states, onChange, availableScenes, onSceneLoad, onNewScene }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-6 mb-6">
      <h1 className="text-3xl font-bold mb-4 text-white">🏛️ Museum Scene State Machine Editor</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Scene Selector (New Intuitive Feature) */}
        <div>
          <label className="block text-sm mb-1 text-gray-300">Load Scene (Library)</label>
          <div className="flex gap-2">
            <select
              onChange={(e) => onSceneLoad(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-blue-500"
              defaultValue=""
            >
              <option value="" disabled>-- Select existing scene --</option>
              {/* Note: availableScenes array must be fetched from RPI backend */}
              {availableScenes?.map(sceneName => (
                <option key={sceneName} value={sceneName}>{sceneName}</option>
              ))}
            </select>
            <button
              onClick={onNewScene}
              className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded text-sm whitespace-nowrap transition"
              title="Create a new empty scene (clears current work)"
            >
              + New
            </button>
          </div>
        </div>

        {/* Scene ID */}
        <div>
          <label className="block text-sm mb-1 text-gray-300">Scene ID</label>
          <input
            type="text"
            value={sceneId}
            onChange={(e) => onChange({ sceneId: e.target.value })}
            className="w-full px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-blue-500"
            placeholder="my_scene"
          />
        </div>

        {/* Version */}
        <div>
          <label className="block text-sm mb-1 text-gray-300">Version</label>
          <input
            type="text"
            value={version}
            onChange={(e) => onChange({ version: e.target.value })}
            className="w-full px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-blue-500"
            placeholder="2.0"
          />
        </div>

        {/* Initial State */}
        <div>
          <label className="block text-sm mb-1 text-gray-300">Initial State</label>
          <select
            value={initialState}
            onChange={(e) => onChange({ initialState: e.target.value })}
            className="w-full px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select initial state...</option>
            {states.map(state => (
              <option key={state.id} value={state.name}>{state.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Description */}
      <div className="mt-4">
        <label className="block text-sm mb-1 text-gray-300">Description</label>
        <input
          type="text"
          value={description}
          onChange={(e) => onChange({ description: e.target.value })}
          className="w-full px-3 py-2 bg-gray-700 rounded focus:ring-2 focus:ring-blue-500"
          placeholder="Scene description"
        />
      </div>

      {/* Global Prefix Info */}
      <div className="mt-4 p-3 bg-indigo-900 rounded border border-indigo-600">
        <div className="text-sm">
          <span className="text-indigo-300">🌐 Global MQTT Prefix:</span>
          <span className="text-white ml-2 font-mono font-bold">{globalPrefix}</span>
          <span className="text-gray-400 ml-2">(click Settings to change)</span>
        </div>
      </div>
    </div>
  );
};

export default Header;