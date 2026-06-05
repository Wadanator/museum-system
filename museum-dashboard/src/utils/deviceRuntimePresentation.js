export const getDeviceRuntimeTone = (runtimeState) => {
  if (!runtimeState?.entry) return 'unknown';
  if (runtimeState.isStale) return 'unknown';
  if (runtimeState.isPending) return 'pending';
  if (runtimeState.confirmedState === 'ON') return 'on';
  if (runtimeState.confirmedState === 'OFF') return 'off';
  return 'unknown';
};

export const getDeviceRuntimeLabel = (runtimeState) => {
  if (!runtimeState?.entry) return 'UNKNOWN';
  if (runtimeState.isStale) return 'STALE';
  if (runtimeState.isPending) return 'PENDING';
  return runtimeState.displayState || runtimeState.confirmedState || 'UNKNOWN';
};
