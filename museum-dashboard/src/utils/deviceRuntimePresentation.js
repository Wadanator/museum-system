const ACTIVE_STATES = new Set(['ON', 'OPEN', 'OPENING', 'CLOSING']);
const INACTIVE_STATES = new Set(['OFF', 'CLOSED', 'STOPPED']);

export const getDeviceRuntimeTone = (runtimeState) => {
  if (!runtimeState?.entry) return 'unknown';
  if (runtimeState.isStale) return 'unknown';
  if (runtimeState.isPending) return 'pending';
  if (ACTIVE_STATES.has(runtimeState.confirmedState)) return 'on';
  if (INACTIVE_STATES.has(runtimeState.confirmedState)) return 'off';
  return 'unknown';
};

export const getDeviceRuntimeLabel = (runtimeState) => {
  if (!runtimeState?.entry) return 'UNKNOWN';
  if (runtimeState.isStale) return 'STALE';
  if (runtimeState.isPending) return 'PENDING';
  return runtimeState.displayState || runtimeState.confirmedState || 'UNKNOWN';
};
