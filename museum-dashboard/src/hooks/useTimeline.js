import { useRef, useEffect } from 'react';

/**
 * useClipDrag — native pointer-event drag for a single timeline clip.
 *
 * Strategy:
 *   - pointerdown: native listener on the element (fires before React synthetic events
 *     and before dnd-kit, because useEffect attaches it directly to the DOM node)
 *   - pointermove / pointerup: document capture-phase listeners
 *     (capture = true means they fire before ANY other handler, including dnd-kit)
 *
 * Elements with [data-no-drag] (e.g. delete button) skip drag activation.
 *
 * click vs drag: if pointer moved < DRAG_THRESHOLD_PX on up → onClick fires instead.
 *
 * Returns { ref } — attach to the clip root div.
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
  const ref      = useRef(null);
  const startRef = useRef(null);
  const liveRef  = useRef(null);
  // Always keep liveRef current so closures inside the effect never go stale
  liveRef.current = { item, pixelsPerSecond, snapEnabled, snapInterval, onMove, onCommit, onClick };

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    function calcAt(clientX) {
      const { pixelsPerSecond: pps, snapEnabled: se, snapInterval: si } = liveRef.current;
      const raw = Math.max(0, startRef.current.originalAt + (clientX - startRef.current.clientX) / pps);
      return +(se ? Math.round(raw / si) * si : raw).toFixed(2);
    }

    // Capture-phase: fires before dnd-kit and React synthetic handlers
    function handleMove(e) {
      if (!startRef.current) return;
      if (Math.abs(e.clientX - startRef.current.clientX) > DRAG_THRESHOLD_PX) {
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
      document.removeEventListener('pointermove', handleMove, true);
      document.removeEventListener('pointerup',   handleUp,   true);
    }

    function handleDown(e) {
      if (e.target.closest('[data-no-drag]')) return;
      e.stopPropagation();
      e.stopImmediatePropagation();
      startRef.current = { clientX: e.clientX, originalAt: liveRef.current.item.at, dragged: false };
      document.addEventListener('pointermove', handleMove, true);
      document.addEventListener('pointerup',   handleUp,   true);
    }

    el.addEventListener('pointerdown', handleDown);
    return () => {
      el.removeEventListener('pointerdown', handleDown);
      // Safety cleanup if component unmounts mid-drag
      document.removeEventListener('pointermove', handleMove, true);
      document.removeEventListener('pointerup',   handleUp,   true);
    };
  }, []); // empty — all values via liveRef

  return { ref };
}
