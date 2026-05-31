import React, { useMemo } from 'react';

const PLAY_VIDEO_COMMAND = 'PLAY_VIDEO';
const SIMPLE_VIDEO_COMMANDS = ['STOP_VIDEO', 'PAUSE', 'RESUME'];

const parseVideoMessage = (message = '') => {
  const trimmed = message.trim();

  if (!trimmed) {
    return {
      mode: PLAY_VIDEO_COMMAND,
      file: '',
      customMessage: ''
    };
  }

  if (trimmed.startsWith(`${PLAY_VIDEO_COMMAND}:`)) {
    const [, file = ''] = trimmed.split(':');
    return {
      mode: PLAY_VIDEO_COMMAND,
      file,
      customMessage: trimmed
    };
  }

  const upper = trimmed.toUpperCase();
  if (SIMPLE_VIDEO_COMMANDS.includes(upper)) {
    return {
      mode: upper,
      file: '',
      customMessage: upper
    };
  }

  return {
    mode: 'CUSTOM',
    file: '',
    customMessage: trimmed
  };
};

const buildVideoMessage = ({ mode, file, customMessage }) => {
  if (mode === PLAY_VIDEO_COMMAND) {
    return `${PLAY_VIDEO_COMMAND}:${file || ''}`;
  }

  if (SIMPLE_VIDEO_COMMANDS.includes(mode)) {
    return mode;
  }

  return customMessage || '';
};

const VideoControls = ({ action, onChange }) => {
  const parsed = useMemo(
    () => parseVideoMessage(action.message || ''),
    [action.message]
  );

  const generatedMessage = buildVideoMessage(parsed);

  const updateMessage = (updates) => {
    const next = { ...parsed, ...updates };
    const message = buildVideoMessage(next);
    onChange({ ...action, message });
  };

  const handleCommandChange = (mode) => {
    if (mode === 'CUSTOM') {
      updateMessage({ mode, customMessage: parsed.customMessage || '' });
    } else if (mode === PLAY_VIDEO_COMMAND) {
      updateMessage({ mode: PLAY_VIDEO_COMMAND });
    } else {
      updateMessage({ mode });
    }
  };

  const handleFileChange = (file) => {
    updateMessage({ mode: PLAY_VIDEO_COMMAND, file });
  };

  return (
    <div className="space-y-4">
      <div className="bg-pink-900 p-3 rounded border border-pink-600">
        <div className="text-sm text-pink-200 font-semibold">
           Video Player - tlačidlá generujú MQTT príkazy kompatibilné s Raspberry Pi
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-2">Vyber akciu</label>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          <button
            type="button"
            onClick={() => handleCommandChange(PLAY_VIDEO_COMMAND)}
            className={`px-3 py-2 rounded text-sm transition border ${
              parsed.mode === PLAY_VIDEO_COMMAND
                ? 'bg-pink-600 border-pink-400'
                : 'bg-gray-600 border-gray-500 hover:bg-gray-500'
            }`}
          >
             PLAY_VIDEO
          </button>
          {SIMPLE_VIDEO_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              type="button"
              onClick={() => handleCommandChange(cmd)}
              className={`px-3 py-2 rounded text-sm transition border ${
                parsed.mode === cmd
                  ? 'bg-pink-600 border-pink-400'
                  : 'bg-gray-600 border-gray-500 hover:bg-gray-500'
              }`}
            >
              {cmd === 'STOP_VIDEO' && ' '}
              {cmd === 'PAUSE' && ' '}
              {cmd === 'RESUME' && ' '}
              {cmd}
            </button>
          ))}
          <button
            type="button"
            onClick={() => handleCommandChange('CUSTOM')}
            className={`px-3 py-2 rounded text-sm transition border ${
              parsed.mode === 'CUSTOM'
                ? 'bg-pink-600 border-pink-400'
                : 'bg-gray-600 border-gray-500 hover:bg-gray-500'
            }`}
          >
             Manuálne
          </button>
        </div>
      </div>

      {parsed.mode === PLAY_VIDEO_COMMAND && (
        <div className="space-y-3 bg-gray-800 p-3 rounded border border-gray-600">
          <div>
            <label className="block text-xs text-gray-300 mb-1">Video súbor</label>
            <input
              type="text"
              value={parsed.file}
              onChange={(e) => handleFileChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded text-sm focus:ring-2 focus:ring-pink-500 font-mono"
              placeholder="scary.mp4"
            />
            <p className="text-xs text-gray-400 mt-1">
               Zadaj názov súboru presne tak, ako ho očakáva Raspberry Pi.
            </p>
          </div>
        </div>
      )}

      {parsed.mode === 'CUSTOM' && (
        <div className="bg-yellow-900/50 p-3 rounded border border-yellow-700">
          <label className="block text-xs text-yellow-200 mb-1">
            Manuálny príkaz (pre pokročilých)
          </label>
          <input
            type="text"
            value={parsed.customMessage}
            onChange={(e) => updateMessage({ customMessage: e.target.value })}
            className="w-full px-3 py-2 bg-yellow-800/70 rounded text-sm font-mono border border-yellow-600 focus:ring-2 focus:ring-yellow-400"
            placeholder="PLAY_VIDEO:scary.mp4"
          />
          <p className="text-xs text-yellow-200 mt-1">
            Toto pole použi iba v prípade, že potrebuješ netypický príkaz.
          </p>
        </div>
      )}

      <div className="bg-gray-800 p-3 rounded border border-gray-700">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">
          MQTT Správa
        </div>
        <code className="block text-sm font-mono text-pink-100 break-words">
          {generatedMessage}
        </code>
      </div>
    </div>
  );
};

export default VideoControls;