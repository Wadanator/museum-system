/**
 * TimeRuler - adaptive time axis.
 *
 * Major interval: smallest of [0.5, 1, 2, 5, 10] where interval*pps >= 60px
 * Minor interval: finest of [0.1, 0.5] where interval*pps >= 12px AND < major
 * Minimum resolution: 0.1 s - never finer.
 */

const MAJOR_INTERVALS = [0.5, 1, 2, 5, 10];
const MINOR_INTERVALS = [0.1, 0.5];
const MIN_MAJOR_PX    = 60;
const MIN_MINOR_PX    = 12;

function pickMajor(pps) {
  return MAJOR_INTERVALS.find((i) => i * pps >= MIN_MAJOR_PX) ?? 10;
}

function pickMinor(pps, major) {
  return MINOR_INTERVALS.find((i) => i * pps >= MIN_MINOR_PX && i < major) ?? null;
}

export default function TimeRuler({ durationSeconds, pixelsPerSecond }) {
  const major = pickMajor(pixelsPerSecond);
  const minor = pickMinor(pixelsPerSecond, major);

  // Use integer steps scaled ×10 to avoid floating-point accumulation drift
  const step    = Math.round((minor ?? major) * 10);
  const majorAt = Math.round(major * 10);
  const total   = Math.round(durationSeconds * 10);

  const ticks = [];
  for (let t = 0; t <= total; t += step) {
    const s       = t / 10;
    const isMajor = t % majorAt === 0;
    ticks.push({ s, isMajor });
  }

  return (
    <div className="se2-tl-ruler" style={{ minWidth: durationSeconds * pixelsPerSecond }}>
      {ticks.map(({ s, isMajor }) => (
        <div
          key={s}
          className={`se2-tl-tick${isMajor ? ' se2-tl-tick--major' : ''}`}
          style={{ left: s * pixelsPerSecond }}
        >
          {isMajor && <span>{s}s</span>}
        </div>
      ))}
    </div>
  );
}
