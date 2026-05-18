import { useRef } from 'react';

/**
 * Pointer-event drag hook for a single timeline clip.
 *
 * Uses native window-level listeners for pointermove/pointerup so that:
 *   - drag continues outside the clip element boundary
 *   - React synthetic event system and dnd-kit do NOT interfere
 *
 * Distinguishes a click (pointer-up with <DRAG_THRESHOLD_PX movement) from
 * a drag. On click, `onClick` is called instead of `onCommit`.
 *
 * @param {object}   params.item            - timeline item with `at` (seconds)
 * @param {number}   params.pixelsPerSecond - current zoom level
 * @param {boolean}  params.snapEnabled     - whether to snap to snapInterval
 * @param {number}   [params.snapInterval]  - snap grid in seconds (default 0.1)
 * @param {function} params.onMove          - (itemId, newAt) => void — live update while dragging
 * @param {function} params.onCommit        - (itemId, newAt) => void — final commit on pointer-up
 * @param {function} [params.onClick]       - () => void — fired on click (no significant drag)
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
  // Keep a ref so native listeners always see fresh callbacks/props
  const liveRef = useRef(null);
  liveRef.current = { item, pixelsPerSecond, snapEnabled, snapInterval, onMove, onCommit, onClick };

  const startRef = useRef(null);

  function onPointerDown(e) {
    // Prevent dnd-kit PointerSensor from activating
    e.stopPropagation();
    e.nativeEvent.stopImmediatePropagation();

    startRef.current = { clientX: e.clientX, originalAt: item.at, dragged: false };

    function snap(seconds) {
      const { snapEnabled: se, snapInterval: si } = liveRef.current;
      return se ? Math.round(seconds / si) * si : seconds;
    }

    function calcAt(clientX) {
      const { pixelsPerSecond: pps } = liveRef.current;
      const deltaX = clientX - startRef.current.clientX;
      const raw    = Math.max(0, startRef.current.originalAt + deltaX / pps);
      return +snap(raw).toFixed(2);
    }

    function handleMove(ev) {
      if (!startRef.current) return;
      const dx = Math.abs(ev.clientX - startRef.current.clientX);
      if (dx > DRAG_THRESHOLD_PX) {
        startRef.current.dragged = true;
        liveRef.current.onMove(liveRef.current.item.id, calcAt(ev.clientX));
      }
    }

    function handleUp(ev) {
      if (!startRef.current) return;
      if (startRef.current.dragged) {
        liveRef.current.onCommit(liveRef.current.item.id, calcAt(ev.clientX));
      } else {
        liveRef.current.onClick?.();
      }
      startRef.current = null;
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup',   handleUp);
    }

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup',   handleUp);
  }

  // Only pointerDown is a React handler; move/up use native window listeners
  return { onPointerDown };
}
