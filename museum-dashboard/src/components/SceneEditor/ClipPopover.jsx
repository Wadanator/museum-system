import { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { X } from 'lucide-react';

/**
 * ClipPopover - inline editor for a single timeline clip.
 * Rendered via a React portal so it escapes the overflow-hidden scroll container.
 * Positioned with `position: fixed` relative to the clip's screen rect.
 *
 * Closes on:
 *   - Click outside
 *   - Escape key
 *   - Enter key (commits the edit)
 */
export default function ClipPopover({ item, anchorRect, onUpdate, onClose }) {
  const ref          = useRef(null);
  const committedRef = useRef(false); // guard: onBlur + outside-click can both fire at once
  const [at,      setAt]      = useState(String(item.at));
  const [topic,   setTopic]   = useState(item.topic   ?? '');
  const [message, setMessage] = useState(item.message ?? '');

  const messageLabel = item.action === 'mqtt'
    ? 'Správa'
    : item.action === 'image'
      ? 'Obrázok'
      : 'Súbor';

  const messagePlaceholder = item.action === 'image'
    ? 'SHOW:wallpaper.png | CLEAR'
    : item.action === 'video'
      ? 'PLAY_VIDEO:file.mp4'
      : item.action === 'audio'
        ? 'PLAY:file.wav:1.0'
        : '';

  // Position: above the clip when there's room, else below
  const style = anchorRect ? (() => {
    const popH = 160;
    if (anchorRect.top >= popH + 8) {
      return {
        position: 'fixed',
        bottom: `${window.innerHeight - anchorRect.top + 6}px`,
        left:   `${anchorRect.left}px`,
      };
    }
    return {
      position: 'fixed',
      top:  `${anchorRect.bottom + 6}px`,
      left: `${anchorRect.left}px`,
    };
  })() : { position: 'fixed', top: 0, left: 0 };

  // Close on outside click (capture phase to beat stopImmediatePropagation on clips)
  useEffect(() => {
    function handlePointer(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    function handleKey(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('pointerdown', handlePointer, true);
    document.addEventListener('keydown',     handleKey);
    return () => {
      document.removeEventListener('pointerdown', handlePointer, true);
      document.removeEventListener('keydown',     handleKey);
    };
  }, [onClose]);

  function commit() {
    if (committedRef.current) return; // already committed - ignore duplicate call
    committedRef.current = true;
    const newAt = parseFloat(at);
    if (!isNaN(newAt) && newAt >= 0) {
      onUpdate(item.id, {
        at: +newAt.toFixed(2),
        message,
        ...(item.action === 'mqtt' ? { topic } : {}),
      });
    }
    onClose();
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') { e.preventDefault(); commit(); }
  }

  return ReactDOM.createPortal(
    <div
      ref={ref}
      className="se2-tl-popover"
      style={style}
      onPointerDown={(e) => { e.stopPropagation(); e.nativeEvent.stopImmediatePropagation(); }}
    >
      <div className="se2-tl-popover-header">
        <span className={`se2-tl-popover-type se2-tl-popover-type--${item.action}`}>
          {item.action.toUpperCase()}
        </span>
        <button className="se2-tl-popover-close" onClick={onClose} type="button" title="Zavrieť">
          <X size={12} />
        </button>
      </div>

      <div className="se2-tl-popover-fields">
        <label className="se2-tl-popover-label">
          Čas (s)
          <input
            className="se2-tl-popover-input"
            type="number"
            step="0.1"
            min="0"
            value={at}
            onChange={(e) => setAt(e.target.value)}
            onBlur={commit}
            onKeyDown={handleKeyDown}
            autoFocus
          />
        </label>

        {item.action === 'mqtt' && (
          <label className="se2-tl-popover-label">
            Topic
            <input
              className="se2-tl-popover-input"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onBlur={commit}
              onKeyDown={handleKeyDown}
              spellCheck={false}
            />
          </label>
        )}

        <label className="se2-tl-popover-label">
          {messageLabel}
          <input
            className="se2-tl-popover-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onBlur={commit}
            onKeyDown={handleKeyDown}
            placeholder={messagePlaceholder}
            spellCheck={false}
          />
        </label>
      </div>
    </div>,
    document.body,
  );
}
