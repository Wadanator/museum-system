import React from 'react';

const VideoControls = ({ action, onChange }) => {
  return (
    <div className="space-y-3">
      <div className="bg-pink-900 p-3 rounded border border-pink-600">
        <div className="text-sm text-pink-200 font-semibold">
          🎬 Video Player - Formát: PLAY_VIDEO:file.mp4
        </div>
      </div>
      
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Video Príkaz (príklady)
        </label>
        <input
          type="text"
          value={action.message || ''}
          onChange={(e) => onChange({ ...action, message: e.target.value })}
          className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-pink-500 font-mono"
          placeholder="PLAY_VIDEO:scary.mp4"
        />
        <div className="text-xs text-gray-500 mt-2 space-y-1">
          <div>💡 <strong>PLAY_VIDEO:scary.mp4</strong> - Prehraj video súbor</div>
          <div>💡 <strong>STOP_VIDEO</strong> - Zastav video</div>
          <div>💡 <strong>PAUSE</strong> - Pozastav</div>
          <div>💡 <strong>RESUME</strong> - Pokračuj</div>
        </div>
      </div>
      
      <div>
        <label className="block text-xs text-gray-400 mb-2">Rýchle príkazy</label>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => onChange({ ...action, message: 'STOP_VIDEO' })}
            className="px-3 py-2 bg-pink-600 hover:bg-pink-700 rounded text-sm"
          >
            ⏹️ STOP_VIDEO
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...action, message: 'PAUSE' })}
            className="px-3 py-2 bg-pink-600 hover:bg-pink-700 rounded text-sm"
          >
            ⏸️ PAUSE
          </button>
          <button
            type="button"
            onClick={() => onChange({ ...action, message: 'RESUME' })}
            className="px-3 py-2 bg-pink-600 hover:bg-pink-700 rounded text-sm"
          >
            ⏯️ RESUME
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoControls;