import React, { useMemo } from 'react';

const PLAY_COMMAND = 'PLAY';
const SIMPLE_COMMANDS = ['STOP', 'PAUSE', 'RESUME'];

const clampVolume = (value) => {
  if (Number.isNaN(value)) return 1;
  return Math.min(1, Math.max(0, value));
};

const parseAudioMessage = (message = '') => {
  const trimmed = message.trim();

  if (!trimmed) {
    return {
      mode: PLAY_COMMAND,
      file: '',
      volume: 1,
      customMessage: ''
    };
  }

  if (trimmed.startsWith(`${PLAY_COMMAND}:`)) {
    const [, file = '', volume = '1'] = trimmed.split(':');
    const numericVolume = parseFloat(volume);
    const safeVolume = Number.isNaN(numericVolume)
      ? 1
      : clampVolume(numericVolume);
    return {
      mode: PLAY_COMMAND,
      file,
      volume: safeVolume,
      customMessage: trimmed
    };
  }

  const upper = trimmed.toUpperCase();
  if (SIMPLE_COMMANDS.includes(upper)) {
    return {
      mode: upper,
      file: '',
      volume: 1,
      customMessage: upper
    };
  }

  return {
    mode: 'CUSTOM',
    file: '',
    volume: 1,
    customMessage: trimmed
  };
};

const buildAudioMessage = ({ mode, file, volume, customMessage }) => {
  if (mode === PLAY_COMMAND) {
    const numericVolume = parseFloat(volume);
    const safeVolume = Number.isNaN(numericVolume)
      ? 1
      : clampVolume(numericVolume);
    const formattedVolume = Math.round(safeVolume * 100) / 100;
    return `${PLAY_COMMAND}:${file || ''}:${formattedVolume}`;
  }

  if (SIMPLE_COMMANDS.includes(mode)) {
    return mode;
  }

  return customMessage || '';
};

const AudioControls = ({ action, onChange }) => {
  const parsed = useMemo(
    () => parseAudioMessage(action.message || ''),
    [action.message]
  );

  const generatedMessage = buildAudioMessage(parsed);

  const updateMessage = (updates) => {
    const next = { ...parsed, ...updates };
    const message = buildAudioMessage(next);
    onChange({ ...action, message });
  };

  const handleCommandChange = (mode) => {
    if (mode === 'CUSTOM') {
      updateMessage({ mode, customMessage: parsed.customMessage || '' });
    } else if (mode === PLAY_COMMAND) {
      updateMessage({ mode: PLAY_COMMAND });
    } else {
      updateMessage({ mode });
    }
  };

  const handleFileChange = (file) => {
    updateMessage({ mode: PLAY_COMMAND, file });
  };

  const handleVolumeChange = (volume) => {
    updateMessage({ mode: PLAY_COMMAND, volume: clampVolume(volume) });
  };

  return (
    <div className="space-y-4">
      <div className="bg-purple-900 p-3 rounded border border-purple-600">
        <div className="text-sm text-purple-200 font-semibold">
          🎵 Audio Player - tlačidlá generujú MQTT príkazy 100% kompatibilné s Raspberry Pi
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-2">Vyber akciu</label>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          <button
            type="button"
            onClick={() => handleCommandChange(PLAY_COMMAND)}
            className={`px-3 py-2 rounded text-sm transition border ${
              parsed.mode === PLAY_COMMAND
                ? 'bg-purple-600 border-purple-400'
                : 'bg-gray-600 border-gray-500 hover:bg-gray-500'
            }`}
          >
            ▶️ PLAY
          </button>
          {SIMPLE_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              type="button"
              onClick={() => handleCommandChange(cmd)}
              className={`px-3 py-2 rounded text-sm transition border ${
                parsed.mode === cmd
                  ? 'bg-purple-600 border-purple-400'
                  : 'bg-gray-600 border-gray-500 hover:bg-gray-500'
              }`}
            >
              {cmd === 'STOP' && '⏹️ '}
              {cmd === 'PAUSE' && '⏸️ '}
              {cmd === 'RESUME' && '⏯️ '}
              {cmd}
            </button>
          ))}
          <button
            type="button"
            onClick={() => handleCommandChange('CUSTOM')}
            className={`px-3 py-2 rounded text-sm transition border ${
              parsed.mode === 'CUSTOM'
                ? 'bg-purple-600 border-purple-400'
                : 'bg-gray-600 border-gray-500 hover:bg-gray-500'
            }`}
          >
            ✏️ Manuálne
          </button>
        </div>
      </div>

      {parsed.mode === PLAY_COMMAND && (
        <div className="space-y-3 bg-gray-800 p-3 rounded border border-gray-600">
          <div>
            <label className="block text-xs text-gray-300 mb-1">Audio súbor</label>
            <input
              type="text"
              value={parsed.file}
              onChange={(e) => handleFileChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 rounded text-sm focus:ring-2 focus:ring-purple-500 font-mono"
              placeholder="intro.mp3"
            />
            <p className="text-xs text-gray-400 mt-1">
              💡 Zadaj názov súboru tak, ako ho používa tvoj Raspberry Pi.
            </p>
          </div>

          <div>
            <label className="block text-xs text-gray-300 mb-1">Hlasitosť (0 - 1)</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={parsed.volume}
                onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                className="flex-1"
              />
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={parsed.volume}
                onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                className="w-20 px-2 py-1 bg-gray-700 rounded text-sm font-mono"
              />
            </div>
            <div className="flex gap-2 mt-2">
              {[0.5, 0.8, 1].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => handleVolumeChange(preset)}
                  className="px-2 py-1 bg-purple-600 hover:bg-purple-700 rounded text-xs"
                >
                  {preset}
                </button>
              ))}
            </div>
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
            placeholder="PLAY:intro.mp3:0.8"
          />
          <p className="text-xs text-yellow-200 mt-1">
            Toto pole sa použije, ak potrebuješ špeciálny príkaz, ktorý nie je
            podporený tlačidlami vyššie.
          </p>
        </div>
      )}

      <div className="bg-gray-800 p-3 rounded border border-gray-700">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">
          MQTT Správa
        </div>
        <code className="block text-sm font-mono text-purple-100 break-words">
          {generatedMessage}
        </code>
      </div>
    </div>
  );
};

export default AudioControls;