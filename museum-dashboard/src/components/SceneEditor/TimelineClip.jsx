import { Trash2 } from 'lucide-react';
import { useClipDrag } from '../../hooks/useTimeline';
import ClipPopover from './ClipPopover';

const LANE_HEIGHT_PX = 52;
const CLIP_TOP_PX    = 6;

/**
 * Build a compact readable label for the clip body.
 * MQTT: last 2 topic segments + message  ->  "light/fire: ON"
 * Audio/Video/Image: compact command/file label  ->  "sfx_alarm"
 */
function clipLabel(item) {
  if (item.action === 'mqtt') {
    const topicShort = item.topic
      ? item.topic.split('/').slice(-2).join('/')
      : '';
    return topicShort
      ? `${topicShort}: ${item.message || '?'}`
      : (item.message || '-');
  }
  if (item.action === 'image') {
    return item.message || '-';
  }
  return item.message ? item.message.replace(/\.[^.]+$/, '') : '-';
}

/**
 * TimelineClip - a single draggable event marker on a timeline track.
 *
 * Drag is handled entirely via native pointer events in useClipDrag (useEffect).
 * The hook returns a ref that must be attached to the root div.
 * Delete button has [data-no-drag] so it never accidentally starts a drag.
 */
export default function TimelineClip({
  item,
  lane = 0,
  pixelsPerSecond,
  snapEnabled,
  isSelected,
  onSelect,
  onClose,
  onMove,
  onCommit,
  onUpdate,
  onDelete,
}) {
  const { ref: clipRef } = useClipDrag({
    item,
    pixelsPerSecond,
    snapEnabled,
    onCommit,
    onClick: onSelect,
  });

  const typeLabel = {
    mqtt: 'MQTT',
    audio: 'AUDIO',
    video: 'VIDEO',
    image: 'IMAGE',
  }[item.action] ?? item.action;
  const tooltip   = `${typeLabel}  *  ${item.topic ? item.topic + ' -> ' : ''}${item.message}  *  @${item.at}s`;
  const topPx     = CLIP_TOP_PX + lane * LANE_HEIGHT_PX;

  return (
    <div
      ref={clipRef}
      className={`se2-tl-clip se2-tl-clip--${item.action}${isSelected ? ' se2-tl-clip--selected' : ''}`}
      style={{ left: item.at * pixelsPerSecond, top: topPx }}
      title={isSelected ? undefined : tooltip}
    >
      <span className="se2-tl-clip-time">@{item.at}s</span>
      <span className="se2-tl-clip-label">{clipLabel(item)}</span>

      {/* data-no-drag prevents the clip's native pointerdown handler from starting a drag */}
      <button
        data-no-drag
        className="se2-tl-clip-delete"
        type="button"
        title="Odstrániť"
        onClick={(e) => { e.stopPropagation(); onDelete(item.id); }}
      >
        <Trash2 size={10} />
      </button>

      {isSelected && (
        <ClipPopover
          item={item}
          anchorRect={clipRef.current?.getBoundingClientRect()}
          onUpdate={onUpdate}
          onClose={onClose}
        />
      )}
    </div>
  );
}
