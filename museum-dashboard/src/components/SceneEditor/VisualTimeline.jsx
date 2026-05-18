import { useState, useMemo, useCallback } from 'react';
import TimeRuler from './TimeRuler';
import TimelineTrack from './TimelineTrack';
import TimelineToolbar from './TimelineToolbar';

const TRACK_TYPES    = ['mqtt', 'audio', 'video'];
const DEFAULT_PPS    = 80;  // pixels per second (zoom default)
const MIN_DURATION_S = 12;  // minimum visible duration in seconds

/**
 * VisualTimeline — FL Studio-style event timeline for one scene state.
 *
 * Layout:
 *   [toolbar]
 *   [scroll container]
 *     [ruler row]   — 64 px label spacer + TimeRuler
 *     [MQTT  row]   — 64 px label        + TimelineTrack (droppable)
 *     [AUDIO row]   — 64 px label        + TimelineTrack (droppable)
 *     [VIDEO row]   — 64 px label        + TimelineTrack (droppable)
 *
 * Clips are events (points in time, not intervals).
 * Clip drag uses native pointer events via useClipDrag — zero re-renders during drag.
 * Palette → track drop uses dnd-kit useDroppable; the actual item creation
 * is handled one level up in SceneEditorView.handleDragEnd.
 *
 * Callbacks received from StatePanel/SceneEditorView use signature
 *   (stateId, itemId, partial) — so we bind stateId here before passing down.
 */
export default function VisualTimeline({
  stateId,
  timeline,
  onMove,
  onCommit,
  onDelete,
}) {
  const [pixelsPerSecond, setPixelsPerSecond] = useState(DEFAULT_PPS);
  const [snapEnabled,     setSnapEnabled]     = useState(true);

  // Compute canvas duration: at least MIN_DURATION_S, or max(at) + 5 s buffer
  const maxAt = useMemo(
    () => timeline.reduce((m, item) => Math.max(m, item.at), 0),
    [timeline],
  );
  const durationSeconds = Math.max(MIN_DURATION_S, Math.ceil(maxAt) + 5);
  const trackWidth      = durationSeconds * pixelsPerSecond;

  // Split clips by action type for the three tracks
  const byType = useMemo(() => ({
    mqtt:  timeline.filter((i) => i.action === 'mqtt'),
    audio: timeline.filter((i) => i.action === 'audio'),
    video: timeline.filter((i) => i.action === 'video'),
  }), [timeline]);

  // Bind stateId so child components only need (itemId, ...) args.
  // onMove / onCommit / onDelete all have signature (stateId, itemId, partial).
  const handleMove   = useCallback((itemId, at)      => onMove(stateId,   itemId, { at }),    [stateId, onMove]);
  const handleCommit = useCallback((itemId, at)      => onCommit(stateId, itemId, { at }),    [stateId, onCommit]);
  const handleDelete = useCallback((itemId)          => onDelete(stateId, itemId),            [stateId, onDelete]);
  const handleUpdate = useCallback((itemId, partial) => onMove(stateId,   itemId, partial),   [stateId, onMove]);

  return (
    <div className="se2-tl-root">
      <TimelineToolbar
        pixelsPerSecond={pixelsPerSecond}
        snapEnabled={snapEnabled}
        onZoomChange={setPixelsPerSecond}
        onSnapToggle={setSnapEnabled}
      />

      <div className="se2-tl-scroll">
        {/* Canvas sized to trackWidth + label column (64) + right buffer (32) */}
        <div className="se2-tl-canvas" style={{ width: trackWidth + 96 }}>

          {/* Ruler row */}
          <div className="se2-tl-ruler-row">
            <div className="se2-tl-lbl-col" />
            <TimeRuler
              durationSeconds={durationSeconds}
              pixelsPerSecond={pixelsPerSecond}
            />
          </div>

          {/* One track per action type */}
          {TRACK_TYPES.map((type) => (
            <TimelineTrack
              key={type}
              stateId={stateId}
              type={type}
              items={byType[type]}
              pixelsPerSecond={pixelsPerSecond}
              snapEnabled={snapEnabled}
              trackWidth={trackWidth}
              onMove={handleMove}
              onCommit={handleCommit}
              onDelete={handleDelete}
              onUpdate={handleUpdate}
            />
          ))}

        </div>
      </div>
    </div>
  );
}
