import { useState } from 'react';
import { Cpu, Zap, Lightbulb, GripVertical, Play, Plus, Loader2 } from 'lucide-react';
import { useDraggable } from '@dnd-kit/core';
import { useDevicePalette } from '../../hooks/useDevicePalette';
import { createEmptyAction } from '../../hooks/useSceneEditor';

// ── helpers ───────────────────────────────────────────────────────────────────

const DEVICE_ICONS = { motor: Cpu, light: Lightbulb, relay: Zap };

function DeviceIcon({ deviceType }) {
  const Icon = DEVICE_ICONS[deviceType] ?? Zap;
  return <Icon size={12} />;
}

// ── sub-components ────────────────────────────────────────────────────────────

function PalSection({ label, children }) {
  return (
    <div className="se2-pal-section">
      <div className="se2-pal-section-header">{label}</div>
      {children}
    </div>
  );
}

function DeviceRow({ item, onInsert, disabled }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `pal:mqtt:${item.id}`,
    data: { type: 'palette', actionType: 'mqtt', topic: item.topic, message: 'ON', label: item.label },
  });
  return (
    <div
      ref={setNodeRef}
      className={`se2-pal-device-row${isDragging ? ' se2-pal-row--dragging' : ''}`}
    >
      <button className="se2-pal-grip" {...attributes} {...listeners} type="button" title="Potiahnuť">
        <GripVertical size={12} />
      </button>
      <span className="se2-pal-device-icon"><DeviceIcon deviceType={item.deviceType} /></span>
      <span className="se2-pal-device-name" title={item.topic}>{item.label}</span>
      <div className="se2-pal-quick-btns">
        {item.quickMessages.map((msg) => (
          <button
            key={msg}
            className="se2-pal-quick-btn"
            onClick={() => onInsert(item.topic, msg, 'mqtt')}
            disabled={disabled}
            title={`${item.topic} → ${msg}`}
            type="button"
          >
            {msg}
          </button>
        ))}
      </div>
    </div>
  );
}

function AudioRow({ item, onInsert, onPreview, disabled }) {
  const shortName = item.name.replace(/\.[^.]+$/, '');
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `pal:audio:${item.name}`,
    data: { type: 'palette', actionType: 'audio', topic: null, message: item.insertMessage, label: shortName },
  });
  return (
    <div ref={setNodeRef} className={`se2-pal-media-row${isDragging ? ' se2-pal-row--dragging' : ''}`}>
      <button className="se2-pal-grip" {...attributes} {...listeners} type="button" title="Potiahnuť">
        <GripVertical size={12} />
      </button>
      <span className="se2-pal-media-name" title={item.name}>{shortName}</span>
      <div className="se2-pal-media-btns">
        <button
          className="se2-pal-preview-btn"
          onClick={() => onPreview(item.name)}
          title={`Prehrať ${item.name}`}
          type="button"
        >
          <Play size={11} />
        </button>
        <button
          className="se2-pal-insert-btn"
          onClick={() => onInsert(null, item.insertMessage, 'audio')}
          disabled={disabled}
          title={`Vložiť: ${item.insertMessage}`}
          type="button"
        >
          <Plus size={11} />
        </button>
      </div>
    </div>
  );
}

function VideoRow({ item, onInsert, disabled }) {
  const shortName = item.name.replace(/\.[^.]+$/, '');
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `pal:video:${item.name}`,
    data: { type: 'palette', actionType: 'video', topic: null, message: item.insertMessage, label: shortName },
  });
  return (
    <div ref={setNodeRef} className={`se2-pal-media-row${isDragging ? ' se2-pal-row--dragging' : ''}`}>
      <button className="se2-pal-grip" {...attributes} {...listeners} type="button" title="Potiahnuť">
        <GripVertical size={12} />
      </button>
      <span className="se2-pal-media-name" title={item.name}>{shortName}</span>
      <div className="se2-pal-media-btns">
        <button
          className="se2-pal-insert-btn"
          onClick={() => onInsert(null, item.insertMessage, 'video')}
          disabled={disabled}
          title={`Vložiť: ${item.insertMessage}`}
          type="button"
        >
          <Plus size={11} />
        </button>
      </div>
    </div>
  );
}

// ── main ──────────────────────────────────────────────────────────────────────

export default function EditorPalette({ selectedStateId, onAddAction }) {
  const { motorItems, relayItems, audioItems, videoItems, loading, playMediaFile } =
    useDevicePalette();

  const [targetSection, setTargetSection] = useState('onEnter');

  const noState = !selectedStateId;

  const handleInsert = (topic, message, actionType) => {
    if (!selectedStateId) return;
    const action = {
      ...createEmptyAction(actionType),
      ...(topic ? { topic } : {}),
      message,
    };
    onAddAction(selectedStateId, targetSection, action);
  };

  const isEmpty =
    motorItems.length === 0 &&
    relayItems.length === 0 &&
    audioItems.length === 0 &&
    videoItems.length === 0;

  return (
    <div className="se2-pal-root">

      {/* Target section toggle */}
      <div className="se2-pal-target-row">
        <span className="se2-pal-target-label">Vložiť do:</span>
        <div className="se2-pal-target-toggle">
          {['onEnter', 'onExit'].map((s) => (
            <button
              key={s}
              className={`se2-pal-target-btn${targetSection === s ? ' active' : ''}`}
              onClick={() => setTargetSection(s)}
              type="button"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {noState && (
        <p className="se2-pal-hint">Vyber stav vľavo.</p>
      )}

      {loading ? (
        <div className="se2-pal-loading">
          <Loader2 size={18} className="se2-loading-spinner" />
        </div>
      ) : isEmpty ? (
        <p className="se2-pal-hint">Žiadne zariadenia ani médiá.</p>
      ) : (
        <>
          {motorItems.length > 0 && (
            <PalSection label="Motory">
              {motorItems.map((item) => (
                <DeviceRow
                  key={item.id}
                  item={item}
                  onInsert={handleInsert}
                  disabled={noState}
                />
              ))}
            </PalSection>
          )}

          {relayItems.length > 0 && (
            <PalSection label="Relé / Svetlá">
              {relayItems.map((item) => (
                <DeviceRow
                  key={item.id}
                  item={item}
                  onInsert={handleInsert}
                  disabled={noState}
                />
              ))}
            </PalSection>
          )}

          {audioItems.length > 0 && (
            <PalSection label="Audio">
              {audioItems.map((item) => (
                <AudioRow
                  key={item.name}
                  item={item}
                  onInsert={handleInsert}
                  onPreview={(name) => playMediaFile('audio', name)}
                  disabled={noState}
                />
              ))}
            </PalSection>
          )}

          {videoItems.length > 0 && (
            <PalSection label="Video">
              {videoItems.map((item) => (
                <VideoRow
                  key={item.name}
                  item={item}
                  onInsert={handleInsert}
                  disabled={noState}
                />
              ))}
            </PalSection>
          )}
        </>
      )}
    </div>
  );
}
