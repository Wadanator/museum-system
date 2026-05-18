import { useRef } from 'react';

/**
 * Pointer-event drag hook for a single timeline clip.
 * Uses setPointerCapture so the drag continues even if the pointer
 * leaves the clip element mid-drag.
 *
 * @param {object}   params.item            - timeline item with `at` (seconds)
 * @param {number}   params.pixelsPerSecond - current zoom level
 * @param {boolean}  params.snapEnabled     - whether to snap to snapInterval
 * @param {number}   [params.snapInterval]  - snap grid in seconds (default 0.1)
 * @param {function} params.onMove          - (itemId, newAt) => void — live update while dragging
 * @param {function} params.onCommit        - (itemId, newAt) => void — final commit on pointer-up
 */
export function useClipDrag({
  item,
  pixelsPerSecond,
  snapEnabled,
  snapInterval = 0.1,
  onMove,
  onCommit,
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
    e.currentTarget.setPointerCapture(e.pointerId);
    e.stopPropagation();
    startRef.current = { clientX: e.clientX, originalAt: item.at };
  }

  function onPointerMove(e) {
    if (!startRef.current) return;
    onMove(item.id, calcAt(e.clientX));
  }

  function onPointerUp(e) {
    if (!startRef.current) return;
    onCommit(item.id, calcAt(e.clientX));
    startRef.current = null;
  }

  return { onPointerDown, onPointerMove, onPointerUp };
}
