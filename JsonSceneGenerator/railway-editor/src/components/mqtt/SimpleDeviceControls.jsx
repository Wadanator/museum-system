import React, { useState } from 'react';

const SimpleDeviceControls = ({ action, onChange, commands }) => {
  const [simpleCommand, setSimpleCommand] = useState(action.message || 'ON');

  const handleCommandChange = (cmd) => {
    setSimpleCommand(cmd);
    onChange({ ...action, message: cmd });
  };

  return (
    <div>
      <label className="block text-xs text-gray-400 mb-2">
        Príkaz
      </label>
      <div className="grid grid-cols-3 gap-2">
        {commands.map((cmd) => (
          <button
            key={cmd}
            type="button"
            onClick={() => handleCommandChange(cmd)}
            className={`px-4 py-3 rounded font-semibold transition ${
              simpleCommand === cmd
                ? 'bg-green-600 text-white'
                : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
            }`}
          >
            {cmd}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SimpleDeviceControls;