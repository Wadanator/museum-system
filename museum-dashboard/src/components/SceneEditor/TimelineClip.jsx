import { Trash2 } from 'lucide-react';
import { useClipDrag } from '../../hooks/useTimeline';

const TYPE_LABELS = { mqtt: 'MQTT', audio: 'AUDIO', video: 'VIDEO' };

function shortLabel(message) {
  if (!message) return '—';
  return message.split(':').slice(0, 2).join(':');
}

/**
 * TimelineClip — a single draggable event marker on a timeline track.
 * Position is driven by `item.at * pixelsPerSecond` (CSS left).
 * Drag uses native pointer events via useClipDrag for zero-latency movement.
 */
export default function TimelineClip({
  item,
  pixelsPerSecond,
  snapEnabled,
  onMove,
  onCommit,
  onDelete,
}) {
  const { onPointerDown, onPointerMove, onPointerUp } = useClipDrag({
    item,
    pixelsPerSecond,
    snapEnabled,
    onMove,
    onCommit,
  });

  const typeLabel = TYPE_LABELS[item.action] ?? item.action;
  const tooltip   = `${typeLabel}  •  ${item.topic ? item.topic + ' → ' : ''}${item.message}  •  @${item.at}s`;

  return (
    <div
      className={`se2-tl-clip se2-tl-clip--${item.action}`}
      style={{ left: item.at * pixelsPerSecond }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      title={tooltip}
    >
      <span className="se2-tl-clip-time">@{item.at}s</span>
      <span className="se2-tl-clip-label">{shortLabel(item.message)}</span>
      <button
        className="se2-tl-clip-delete"
        onClick={(e) => { e.stopPropagation(); onDelete(item.id); }}
        onPointerDown={(e) => e.stopPropagation()}
        type="button"
        title="Odstrániť"
      >
        <Trash2 size={10} />
      </button>
    </div>
  );
}
