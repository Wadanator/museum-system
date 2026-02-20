import React, { useState } from 'react';

const MotorControls = ({ action, onChange }) => {
  const parseMotorMessage = () => {
    const msg = action.message || '';
    
    if (msg === 'OFF') {
      return { command: 'OFF', speed: 50, direction: 'L', rampTime: 0 };
    }
    
    if (msg === 'STOP') {
      return { command: 'STOP', speed: 50, direction: 'L', rampTime: 0 };
    }
    
    const parts = msg.split(':');
    if (parts[0] === 'ON') {
      const speed = parseInt(parts[1]) || 50;
      const direction = parts[2] || 'L';
      // RampTime je štvrtý parameter (index 3)
      const rampTime = parts.length > 3 ? parseInt(parts[3]) || 0 : 0;
      
      return {
        command: 'ON',
        speed: speed,
        direction: direction,
        rampTime: rampTime
      };
    }
    
    // Default fallback
    return { command: 'ON', speed: 50, direction: 'L', rampTime: 0 };
  };

  const parsed = parseMotorMessage();
  const [motorCommand, setMotorCommand] = useState(parsed.command);
  const [motorSpeed, setMotorSpeed] = useState(parsed.speed);
  const [motorDirection, setMotorDirection] = useState(parsed.direction);
  const [motorRampTime, setMotorRampTime] = useState(parsed.rampTime);

  const updateMotorMessage = (cmd, speed, dir, rampTime) => {
    let message = '';
    
    if (cmd === 'OFF') {
      message = 'OFF';
    } else if (cmd === 'STOP') {
      message = 'STOP';
    } else if (cmd === 'ON') {
      // VŽDY pošleme aj rampTime, aj keď je 0 (pre konzistenciu parsera)
      const safeRamp = rampTime || 0;
      message = `ON:${speed}:${dir}:${safeRamp}`;
    }
    
    onChange({ ...action, message });
  };

  const handleCommandChange = (cmd) => {
    setMotorCommand(cmd);
    updateMotorMessage(cmd, motorSpeed, motorDirection, motorRampTime);
  };

  const handleSpeedChange = (speed) => {
    setMotorSpeed(speed);
    if (motorCommand === 'ON') {
      updateMotorMessage('ON', speed, motorDirection, motorRampTime);
    }
  };

  const handleDirectionChange = (dir) => {
    setMotorDirection(dir);
    if (motorCommand === 'ON') {
      updateMotorMessage('ON', motorSpeed, dir, motorRampTime);
    }
  };

  const handleRampTimeChange = (time) => {
    const newTime = parseInt(time) || 0;
    setMotorRampTime(newTime < 0 ? 0 : newTime);
    if (motorCommand === 'ON') {
      updateMotorMessage('ON', motorSpeed, motorDirection, newTime);
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
            <label className="block text-xs text-gray-400 mb-1">
              Čas rozbehu (Ramp Time) v ms
            </label>
            <input
              type="number"
              min="0"
              step="100"
              value={motorRampTime}
              onChange={(e) => handleRampTimeChange(e.target.value)}
              className="w-full px-3 py-2 bg-gray-600 rounded text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="0 (okamžite)"
            />
            <div className="text-xs text-gray-500 mt-1">
              💡 0 = Okamžitý štart. Napr. 2000 = Motor sa rozbehne na cieľovú rýchlosť za 2 sekundy.
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