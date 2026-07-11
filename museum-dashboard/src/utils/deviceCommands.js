export const DEFAULT_MOTOR_SPEED = 50;
export const DEFAULT_WINDOW_SPEED = 30;

const normalizePercent = (speed, fallback) => {
  if (speed === null || speed === undefined || speed === '') {
    return fallback;
  }

  const value = Number(speed);
  if (!Number.isFinite(value)) {
    return fallback;
  }

  return Math.min(100, Math.max(0, Math.round(value)));
};

export const normalizeMotorSpeed = (speed, fallback = DEFAULT_MOTOR_SPEED) => (
  normalizePercent(speed, fallback)
);

export const normalizeWindowSpeed = (speed, fallback = DEFAULT_WINDOW_SPEED) => (
  normalizePercent(speed, fallback)
);

export const buildMotorOnCommand = (speed, direction = 'L', rampMs = 0) => {
  const safeSpeed = normalizeMotorSpeed(speed);
  const safeDirection = String(direction).trim().toUpperCase() === 'R' ? 'R' : 'L';
  const safeRamp = Math.max(0, Math.round(Number(rampMs) || 0));
  return `ON:${safeSpeed}:${safeDirection}:${safeRamp}`;
};

export const buildWindowCommand = (action, speed) => {
  const safeAction = String(action).trim().toUpperCase();
  if (safeAction === 'STOP') return 'STOP';

  const safeSpeed = normalizeWindowSpeed(speed);
  if (safeAction === 'OPEN' || safeAction === 'CLOSE') {
    return `${safeAction}:${safeSpeed}`;
  }

  return 'STOP';
};
