import { useState, useMemo } from 'react';
import { useDroppable } from '@dnd-kit/core';
import TimelineClip from './TimelineClip';

const TRACK_LABELS  = {
  mqtt: 'MQTT',
  audio: 'AUDIO',
  video: 'VIDEO',
  image: 'IMAGE',
};
const CLIP_WIDTH_PX = 130; // must match CSS .se2-tl-clip width

/**
 * Assigns a lane index to each clip so that overlapping clips
 * (closer than one clip-width in seconds) stack vertically instead of
 * overlapping. Returns a new array with a `lane` property on each item.
 */
function assignLanes(items, pixelsPerSecond) {
  const clipDurationS = CLIP_WIDTH_PX / pixelsPerSecond;
  const sorted        = [...items].sort((a, b) => a.at - b.at);
  const laneEndAt     = []; // tracks the end-time of the last clip in each lane

  return sorted.map((item) => {
    let lane = laneEndAt.findIndex((endAt) => item.at >= endAt);
    if (lane === -1) {
      lane = laneEndAt.length;
      laneEndAt.push(item.at + clipDurationS);
    } else {
      laneEndAt[lane] = item.at + clipDurationS;
    }
    return { ...item, lane };
  });
}

/**
 * TimelineTrack - one horizontal track (MQTT / Audio / Video / Image).
 *
 * - Acts as a dnd-kit droppable (palette -> track drop).
 * - Computes lane stacking so clips never overlap visually.
 * - Track height grows automatically with lane count.
 * - Maintains `selectedId` state for the clip popover.
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
  onUpdate,
}) {
  const [selectedId, setSelectedId] = useState(null);

  const { setNodeRef, isOver } = useDroppable({
    id:   `timeline-track:${stateId}:${type}`,
    // pixelsPerSecond is included so SceneEditorView can compute the drop time
    data: { zone: 'timeline-track', stateId, trackType: type, pixelsPerSecond },
  });

  const lanedItems = useMemo(
    () => assignLanes(items, pixelsPerSecond),
    [items, pixelsPerSecond],
  );

  const laneCount = lanedItems.length > 0
    ? Math.max(...lanedItems.map((i) => i.lane)) + 1
    : 1;

  return (
    <div className="se2-tl-track-row">
      <div className={`se2-tl-track-label se2-tl-track-label--${type}`}>
        {TRACK_LABELS[type] ?? type.toUpperCase()}
      </div>

      <div
        ref={setNodeRef}
        className={`se2-tl-track${isOver ? ' se2-tl-track--over' : ''}`}
        style={{
          width: trackWidth,
          '--se2-tl-pps':        `${pixelsPerSecond}px`,
          '--se2-tl-lane-count': laneCount,
        }}
      >
        {lanedItems.map((item) => (
          <TimelineClip
            key={item.id}
            item={item}
            lane={item.lane}
            pixelsPerSecond={pixelsPerSecond}
            snapEnabled={snapEnabled}
            isSelected={selectedId === item.id}
            onSelect={() => setSelectedId(item.id)}
            onClose={() => setSelectedId(null)}
            onMove={onMove}
            onCommit={onCommit}
            onDelete={onDelete}
            onUpdate={onUpdate}
          />
        ))}
      </div>
    </div>
  );
}
