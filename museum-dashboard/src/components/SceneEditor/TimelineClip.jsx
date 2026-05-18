import { useRef } from 'react';
import { Trash2 } from 'lucide-react';
import { useClipDrag } from '../../hooks/useTimeline';
import ClipPopover from './ClipPopover';

const LANE_HEIGHT_PX = 52;
const CLIP_TOP_PX    = 6;

function shortLabel(message) {
  if (!message) return '—';
  return message.split(':').slice(0, 2).join(':');
}

/**
 * TimelineClip — a single draggable event marker on a timeline track.
 *
 * Position:
 *   left = item.at * pixelsPerSecond
 *   top  = CLIP_TOP_PX + lane * LANE_HEIGHT_PX   (lane stacking)
 *
 * Interaction:
 *   - Drag  → moves the clip (pointer capture, zero-latency)
 *   - Click → opens ClipPopover inline editor (portal, position: fixed)
 *   - ×     → deletes the clip
 */
export default function TimelineClip({
  item,
  lane = 0,
  pixelsPerSecond,
  snapEnabled,
  isSelected,
  onSelect,
  onMove,
  onCommit,
  onUpdate,
  onDelete,
}) {
  const clipRef = useRef(null);

  const { onPointerDown, onPointerMove, onPointerUp } = useClipDrag({
    item,
    pixelsPerSecond,
    snapEnabled,
    onMove,
    onCommit,
    onClick: onSelect,
  });

  const typeLabel = { mqtt: 'MQTT', audio: 'AUDIO', video: 'VIDEO' }[item.action] ?? item.action;
  const tooltip   = `${typeLabel}  •  ${item.topic ? item.topic + ' → ' : ''}${item.message}  •  @${item.at}s`;
  const topPx     = CLIP_TOP_PX + lane * LANE_HEIGHT_PX;

  return (
    <div
      ref={clipRef}
      className={`se2-tl-clip se2-tl-clip--${item.action}${isSelected ? ' se2-tl-clip--selected' : ''}`}
      style={{ left: item.at * pixelsPerSecond, top: topPx }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      title={isSelected ? undefined : tooltip}
    >
      <span className="se2-tl-clip-time">@{item.at}s</span>
      <span className="se2-tl-clip-label">{shortLabel(item.message)}</span>

      <button
        className="se2-tl-clip-delete"
        type="button"
        title="Odstrániť"
        onClick={(e)      => { e.stopPropagation(); onDelete(item.id); }}
        onPointerDown={(e) => { e.stopPropagation(); e.nativeEvent.stopImmediatePropagation(); }}
      >
        <Trash2 size={10} />
      </button>

      {isSelected && (
        <ClipPopover
          item={item}
          anchorRect={clipRef.current?.getBoundingClientRect()}
          onUpdate={onUpdate}
          onClose={onSelect}
        />
      )}
    </div>
  );
}
