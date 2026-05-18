import { useDroppable } from '@dnd-kit/core';
import TimelineClip from './TimelineClip';

const TRACK_LABELS = { mqtt: 'MQTT', audio: 'AUDIO', video: 'VIDEO' };

/**
 * TimelineTrack — one horizontal track (MQTT / Audio / Video).
 * Acts as a dnd-kit droppable so palette items can be dropped onto it.
 * Clips are positioned absolutely via `left = item.at * pixelsPerSecond`.
 */
export default function TimelineTrack({
  stateId,
  type,
  items,
  pixelsPerSecond,
  snapEnabled,
  trackWidth,
  onMove,
  onCommit,
  onDelete,
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `timeline-track:${stateId}:${type}`,
    data: { zone: 'timeline-track', stateId, trackType: type },
  });

  return (
    <div className="se2-tl-track-row">
      <div className={`se2-tl-track-label se2-tl-track-label--${type}`}>
        {TRACK_LABELS[type]}
      </div>

      <div
        ref={setNodeRef}
        className={`se2-tl-track${isOver ? ' se2-tl-track--over' : ''}`}
        style={{
          width: trackWidth,
          '--se2-tl-pps': `${pixelsPerSecond}px`,
        }}
      >
        {items.map((item) => (
          <TimelineClip
            key={item.id}
            item={item}
            pixelsPerSecond={pixelsPerSecond}
            snapEnabled={snapEnabled}
            onMove={onMove}
            onCommit={onCommit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}
