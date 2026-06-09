import { useState } from 'react';
import {
  GripVertical,
  Play,
  Plus,
  Loader2,
  ChevronDown,
  ChevronRight,
  Image as ImageIcon,
} from 'lucide-react';
import { useDraggable } from '@dnd-kit/core';
import { useDevicePalette } from '../../hooks/useDevicePalette';
import { createEmptyAction } from '../../hooks/useSceneEditor';
import DeviceIcon from '../Devices/DeviceIcon';

function PalSection({ label, open, onToggle, children }) {
  const Chevron = open ? ChevronDown : ChevronRight;
  return (
    <div className="se2-pal-section">
      <div
        className={`se2-pal-section-header${open ? ' se2-pal-section-header--open' : ''}`}
        onClick={onToggle}
      >
        <Chevron size={11} />
        {label}
      </div>
      {open && children}
    </div>
  );
}

function DeviceRow({ item, onInsert, disabled }) {
  const defaultMessage = item.defaultMessage || item.quickMessages?.[0] || 'ON';
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `pal:mqtt:${item.id}`,
    data: {
      type: 'palette',
      actionType: 'mqtt',
      topic: item.topic,
      message: defaultMessage,
      label: item.label,
    },
  });
  return (
    <div
      ref={setNodeRef}
      className={`se2-pal-device-row${isDragging ? ' se2-pal-row--dragging' : ''}`}
    >
      <button className="se2-pal-grip" {...attributes} {...listeners} type="button" title="Potiahnuť">
        <GripVertical size={12} />
      </button>
      <span className="se2-pal-device-icon"><DeviceIcon device={item} size={12} /></span>
      <span className="se2-pal-device-name" title={item.topic}>{item.label}</span>
      <div className="se2-pal-quick-btns">
        {item.quickMessages.map((msg) => (
          <button
            key={msg}
            className="se2-pal-quick-btn"
            onClick={() => onInsert(item.topic, msg, 'mqtt')}
            disabled={disabled}
            title={`${item.topic} -> ${msg}`}
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

function ImageRow({ item, onInsert, onPreview, disabled }) {
  const shortName = item.name.replace(/\.[^.]+$/, '');
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `pal:image:${item.name}`,
    data: { type: 'palette', actionType: 'image', topic: null, message: item.insertMessage, label: shortName },
  });
  return (
    <div ref={setNodeRef} className={`se2-pal-media-row${isDragging ? ' se2-pal-row--dragging' : ''}`}>
      <button className="se2-pal-grip" {...attributes} {...listeners} type="button" title="Potiahnuť">
        <GripVertical size={12} />
      </button>
      <span className="se2-pal-media-icon"><ImageIcon size={12} /></span>
      <span className="se2-pal-media-name" title={item.name}>{shortName}</span>
      <div className="se2-pal-media-btns">
        <button
          className="se2-pal-preview-btn"
          onClick={() => onPreview(item.name)}
          title={`Zobraziť ${item.name}`}
          type="button"
        >
          <Play size={11} />
        </button>
        <button
          className="se2-pal-insert-btn"
          onClick={() => onInsert(null, item.insertMessage, 'image')}
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

export default function EditorPalette({ selectedStateId, onAddAction }) {
  const { motorItems, relayItems, audioItems, videoItems, imageItems, loading, playMediaFile } =
    useDevicePalette();

  const [targetSection, setTargetSection] = useState('onEnter');
  const [openCats, setOpenCats] = useState({
    motors: true,
    relays: false,
    audio: false,
    video: false,
    image: false,
  });
  const toggleCat = (cat) => setOpenCats((prev) => ({ ...prev, [cat]: !prev[cat] }));

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
    videoItems.length === 0 &&
    imageItems.length === 0;

  return (
    <div className="se2-pal-root">
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
            <PalSection label="Motory" open={openCats.motors} onToggle={() => toggleCat('motors')}>
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
            <PalSection label="Relé / Svetlá" open={openCats.relays} onToggle={() => toggleCat('relays')}>
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
            <PalSection label="Audio" open={openCats.audio} onToggle={() => toggleCat('audio')}>
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
            <PalSection label="Video" open={openCats.video} onToggle={() => toggleCat('video')}>
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

          {imageItems.length > 0 && (
            <PalSection label="Obrázky" open={openCats.image} onToggle={() => toggleCat('image')}>
              {imageItems.map((item) => (
                <ImageRow
                  key={item.name}
                  item={item}
                  onInsert={handleInsert}
                  onPreview={(name) => playMediaFile('video', name)}
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
