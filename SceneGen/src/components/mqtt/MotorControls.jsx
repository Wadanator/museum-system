import React, { useState } from 'react';

const MotorControls = ({ action, onChange }) => {
  const parseMotorMessage = () => {
    const msg = action.message || '';
    
    if (msg === 'OFF') {
      return { command: 'OFF', speed: 50, direction: 'L' };
    }
    
    if (msg === 'STOP') {
      return { command: 'STOP', speed: 50, direction: 'L' };
    }
    
    const parts = msg.split(':');
    if (parts[0] === 'ON' && parts.length === 3) {
      return {
        command: 'ON',
        speed: parseInt(parts[1]) || 50,
        direction: parts[2] || 'L'
      };
    }
    
    return { command: 'ON', speed: 50, direction: 'L' };
  };

  const parsed = parseMotorMessage();
  const [motorCommand, setMotorCommand] = useState(parsed.command);
  const [motorSpeed, setMotorSpeed] = useState(parsed.speed);
  const [motorDirection, setMotorDirection] = useState(parsed.direction);

  const updateMotorMessage = (cmd, speed, dir) => {
    let message = '';
    
    if (cmd === 'OFF') {
      message = 'OFF';
    } else if (cmd === 'STOP') {
      message = 'STOP';
    } else if (cmd === 'ON') {
      message = `ON:${speed}:${dir}`;
    }
    
    onChange({ ...action, message });
  };

  const handleCommandChange = (cmd) => {
    setMotorCommand(cmd);
    updateMotorMessage(cmd, motorSpeed, motorDirection);
  };

  const handleSpeedChange = (speed) => {
    setMotorSpeed(speed);
    if (motorCommand === 'ON') {
      updateMotorMessage('ON', speed, motorDirection);
    }
  };

  const handleDirectionChange = (dir) => {
    setMotorDirection(dir);
    if (motorCommand === 'ON') {
      updateMotorMessage('ON', motorSpeed, dir);
    }
  };

  return (
    <>
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Príkaz
        </label>
        <select
          value={motorCommand}
          onChange={(e) => handleCommandChange(e.target.value)}
          className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-blue-500"
        >
          <option value="ON">ON - Zapni motor</option>
          <option value="OFF">OFF - Vypni motor</option>
          <option value="STOP">STOP - Emergency stop</option>
        </select>
      </div>

      {motorCommand === 'ON' && (
        <>
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Rýchlosť (Speed): {motorSpeed}%
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={motorSpeed}
              onChange={(e) => handleSpeedChange(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0%</span>
              <span>50%</span>
              <span>100%</span>
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-2">
              Smer (Direction)
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleDirectionChange('L')}
                className={`flex-1 px-4 py-3 rounded font-semibold transition ${
                  motorDirection === 'L'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
                }`}
              >
                ⬅️ L (Doľava)
              </button>
              <button
                type="button"
                onClick={() => handleDirectionChange('R')}
                className={`flex-1 px-4 py-3 rounded font-semibold transition ${
                  motorDirection === 'R'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
                }`}
              >
                R (Doprava) ➡️
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default MotorControls;