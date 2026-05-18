import { ZoomIn, ZoomOut } from 'lucide-react';
import Button from '../ui/Button';

const MIN_PPS = 40;
const MAX_PPS = 400;
const STEP    = 20;

/**
 * TimelineToolbar — zoom controls (px/s) and snap-to-grid toggle.
 */
export default function TimelineToolbar({
  pixelsPerSecond,
  snapEnabled,
  onZoomChange,
  onSnapToggle,
}) {
  return (
    <div className="se2-tl-toolbar">
      <Button
        variant="ghost"
        size="small"
        icon={ZoomOut}
        cooldown={0}
        onClick={() => onZoomChange(Math.max(MIN_PPS, pixelsPerSecond - STEP))}
        disabled={pixelsPerSecond <= MIN_PPS}
        title="Oddiali"
      />
      <span className="se2-tl-zoom-label">{pixelsPerSecond} px/s</span>
      <Button
        variant="ghost"
        size="small"
        icon={ZoomIn}
        cooldown={0}
        onClick={() => onZoomChange(Math.min(MAX_PPS, pixelsPerSecond + STEP))}
        disabled={pixelsPerSecond >= MAX_PPS}
        title="Priblíži"
      />

      <div className="se2-tl-toolbar-divider" />

      <label className="se2-tl-snap-toggle">
        <input
          type="checkbox"
          checked={snapEnabled}
          onChange={(e) => onSnapToggle(e.target.checked)}
        />
        <span>Snap 0.1s</span>
      </label>
    </div>
  );
}
