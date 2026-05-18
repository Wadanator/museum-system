import { useRef } from 'react';

/**
 * Pointer-event drag hook for a single timeline clip.
 * Uses setPointerCapture so the drag continues even if the pointer
 * leaves the clip element mid-drag.
 *
 * Distinguishes a click (pointer-up without significant movement) from
 * a drag (pointer moved > DRAG_THRESHOLD_PX before pointer-up).
 * When a click is detected, `onClick` is called instead of `onCommit`.
 *
 * @param {object}    params.item            - timeline item with `at` (seconds)
 * @param {number}    params.pixelsPerSecond - current zoom level
 * @param {boolean}   params.snapEnabled     - whether to snap to snapInterval
 * @param {number}    [params.snapInterval]  - snap grid in seconds (default 0.1)
 * @param {function}  params.onMove          - (itemId, newAt) => void — live update while dragging
 * @param {function}  params.onCommit        - (itemId, newAt) => void — final commit on pointer-up
 * @param {function}  [params.onClick]       - () => void — fired on click (no significant drag)
 */

const DRAG_THRESHOLD_PX = 4;

export function useClipDrag({
  item,
  pixelsPerSecond,
  snapEnabled,
  snapInterval = 0.1,
  onMove,
  onCommit,
  onClick,
}) {
  const startRef = useRef(null);

  function snap(seconds) {
    return snapEnabled
      ? Math.round(seconds / snapInterval) * snapInterval
      : seconds;
  }

  function calcAt(clientX) {
    const deltaX = clientX - startRef.current.clientX;
    const raw = Math.max(0, startRef.current.originalAt + deltaX / pixelsPerSecond);
    return +snap(raw).toFixed(2);
  }

  function onPointerDown(e) {
    // stopImmediatePropagation prevents dnd-kit's document-level PointerSensor
    // from intercepting this event and activating a palette drag instead.
    e.stopPropagation();
    e.nativeEvent.stopImmediatePropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    startRef.current = { clientX: e.clientX, originalAt: item.at, dragged: false };
  }

  function onPointerMove(e) {
    if (!startRef.current) return;
    const dx = Math.abs(e.clientX - startRef.current.clientX);
    if (dx > DRAG_THRESHOLD_PX) {
      startRef.current.dragged = true;
      onMove(item.id, calcAt(e.clientX));
    }
  }

  function onPointerUp(e) {
    if (!startRef.current) return;
    if (startRef.current.dragged) {
      onCommit(item.id, calcAt(e.clientX));
    } else {
      onClick?.();
    }
    startRef.current = null;
  }

  return { onPointerDown, onPointerMove, onPointerUp };
}
