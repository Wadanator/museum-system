const getRuntimeTone = (runtimeState) => {
  if (!runtimeState?.entry) return 'unknown';
  if (runtimeState.isStale) return 'unknown';
  if (runtimeState.isPending) return 'pending';
  if (runtimeState.confirmedState === 'ON') return 'on';
  if (runtimeState.confirmedState === 'OFF') return 'off';
  return 'unknown';
};

const getRuntimeLabel = (runtimeState) => {
  if (!runtimeState?.entry) return 'UNKNOWN';
  if (runtimeState.isStale) return 'STALE';
  if (runtimeState.isPending) return 'PENDING';
  return runtimeState.displayState || runtimeState.confirmedState || 'UNKNOWN';
};

export default function DeviceRuntimeIndicator({ runtimeState }) {
  const tone = getRuntimeTone(runtimeState);
  const label = getRuntimeLabel(runtimeState);
  const topic = runtimeState?.entry?.topic || runtimeState?.topic || 'bez runtime dat';

  return (
    <div
      className={`device-runtime-indicator device-runtime-indicator--${tone}`}
      title={`${topic}: ${label}`}
      aria-label={`Stav zariadenia ${label}`}
    >
      <span className="device-runtime-dot" />
      <span className="device-runtime-label">{label}</span>
    </div>
  );
}
