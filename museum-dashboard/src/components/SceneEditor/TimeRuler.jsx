/**
 * TimeRuler — horizontal time axis with major (1 s) and minor (0.5 s) ticks.
 * Minor ticks are only shown when pixelsPerSecond >= 80 (enough space).
 */
export default function TimeRuler({ durationSeconds, pixelsPerSecond }) {
  const ticks = [];

  for (let s = 0; s <= durationSeconds; s += 1) {
    ticks.push({ s, major: true });
    if (pixelsPerSecond >= 80 && s < durationSeconds) {
      ticks.push({ s: s + 0.5, major: false });
    }
  }

  return (
    <div className="se2-tl-ruler" style={{ minWidth: durationSeconds * pixelsPerSecond }}>
      {ticks.map(({ s, major }) => (
        <div
          key={s}
          className={`se2-tl-tick${major ? ' se2-tl-tick--major' : ''}`}
          style={{ left: s * pixelsPerSecond }}
        >
          {major && <span>{s}s</span>}
        </div>
      ))}
    </div>
  );
}
