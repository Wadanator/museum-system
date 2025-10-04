import React from 'react';

const AudioControls = ({ action, onChange }) => {
  return (
    <div className="space-y-3">
      <div className="bg-purple-900 p-3 rounded border border-purple-600">
        <div className="text-sm text-purple-200 font-semibold">
          🎵 Audio Player - Formát: PLAY:file.mp3:0.8
        </div>
      </div>
      
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Audio Príkaz (príklady)
        </label>
        <input
          type="text"
          value={action.message || ''}
          onChange={(e) => onChange({ ...action, message: e.target.value })}
          className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-purple-500 font-mono"
          placeholder="PLAY:intro.mp3:0.8"
        />
        <div className="text-xs text-gray-500 mt-2 space-y-1">
          <div>💡 <strong>PLAY:intro.mp3:0.8</strong> - Prehraj súbor s hlasitosťou 0.8</div>
          <div>💡 <strong>STOP</strong> - Zastav prehrávanie</div>
          <div>💡 <strong>PAUSE</strong> - Pozastav</div>
          <div>💡 <strong>RESUME</strong> - Pokračuj</div>
        </div>
      </div>
      
      <div>
        <label className="block text-xs text-gray-400 mb-2">Rýchle príkazy</label>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => onChange({ ...action, message: 'STOP' })}
            className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded text-sm"
          >
            ⏹️ STOP
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...action, message: 'PAUSE' })}
            className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded text-sm"
          >
            ⏸️ PAUSE
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...action, message: 'RESUME' })}
            className="px-3 py-2 bg-purple-600 hover:bg-purple-700 rounded text-sm"
          >
            ⏯️ RESUME
          </button>
        </div>
      </div>
    </div>
  );
};

export default AudioControls;