import { useRef, useEffect } from 'react';

/**
 * useClipDrag — native pointer-event drag for a single timeline clip.
 *
 * Registers event listeners directly on the DOM element via useEffect so that:
 *   - setPointerCapture redirects all move/up to the element (reliable cross-browser)
 *   - React synthetic event system is bypassed entirely
 *   - dnd-kit PointerSensor never sees pointerdown on a clip
 *
 * Elements with [data-no-drag] attribute (e.g. the delete button) inside the clip
 * are excluded — clicking them does NOT start a drag.
 *
 * Distinguishes click (move < DRAG_THRESHOLD_PX) from drag:
 *   - drag  → onMove (live) + onCommit (on up)
 *   - click → onClick
 *
 * Returns { ref } — attach to the clip's root div.
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
  const ref     = useRef(null);
  const startRef = useRef(null);

  // Keep a mutable ref so the effect closure always sees fresh props/callbacks
  const liveRef = useRef(null);
  liveRef.current = { item, pixelsPerSecond, snapEnabled, snapInterval, onMove, onCommit, onClick };

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

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

    function handleMove(e) {
      if (!startRef.current) return;
      const dx = Math.abs(e.clientX - startRef.current.clientX);
      if (dx > DRAG_THRESHOLD_PX) {
        startRef.current.dragged = true;
        liveRef.current.onMove(liveRef.current.item.id, calcAt(e.clientX));
      }
    }

    function handleUp(e) {
      if (!startRef.current) return;
      if (startRef.current.dragged) {
        liveRef.current.onCommit(liveRef.current.item.id, calcAt(e.clientX));
      } else {
        liveRef.current.onClick?.();
      }
      startRef.current = null;
      el.removeEventListener('pointermove', handleMove);
      el.removeEventListener('pointerup',   handleUp);
    }

    function handleDown(e) {
      // Ignore clicks on elements marked as non-draggable (e.g. delete button)
      if (e.target.closest('[data-no-drag]')) return;

      // Block dnd-kit and any other listeners on the same element
      e.stopPropagation();
      e.stopImmediatePropagation();

      // Capture pointer so move/up go to this element even outside its bounds
      el.setPointerCapture(e.pointerId);
      startRef.current = {
        clientX:    e.clientX,
        originalAt: liveRef.current.item.at,
        dragged:    false,
      };

      el.addEventListener('pointermove', handleMove);
      el.addEventListener('pointerup',   handleUp);
    }

    el.addEventListener('pointerdown', handleDown);
    return () => {
      el.removeEventListener('pointerdown', handleDown);
    };
  }, []); // empty — all values accessed via liveRef

  return { ref };
}
