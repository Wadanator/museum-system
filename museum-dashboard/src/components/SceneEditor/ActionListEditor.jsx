import { GripVertical, Plus, Trash2 } from 'lucide-react';
import { useDroppable } from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import Button from '../ui/Button';
import { createEmptyAction } from '../../hooks/useSceneEditor';

const TYPE_LABELS = { mqtt: 'MQTT', audio: 'AUDIO', video: 'VIDEO', image: 'IMAGE' };
const TYPE_CYCLE  = { mqtt: 'audio', audio: 'video', video: 'image', image: 'mqtt' };
const IMAGE_EXTENSION_RE = /\.(png|jpe?g)$/i;

function defaultMessageForType(action, nextType) {
  const message = action.message || '';

  if (nextType === 'image') {
    if (message.startsWith('SHOW:') || ['CLEAR', 'DEFAULT'].includes(message.toUpperCase())) {
      return message;
    }
    if (message.startsWith('PLAY_VIDEO:')) {
      const filename = message.split(':', 2)[1] || '';
      if (IMAGE_EXTENSION_RE.test(filename)) return `SHOW:${filename}`;
    }
    return 'SHOW:';
  }

  if (nextType === 'video' && action.action === 'image' && message.startsWith('SHOW:')) {
    return `PLAY_VIDEO:${message.split(':', 2)[1] || ''}`;
  }

  return message;
}

function nextTypePatch(action) {
  const nextType = TYPE_CYCLE[action.action || 'mqtt'] || 'mqtt';
  return {
    action: nextType,
    ...(nextType !== 'mqtt' ? { topic: '' } : {}),
    message: defaultMessageForType(action, nextType),
  };
}

/** Single sortable action row with drag handle */
function SortableActionRow({ action, stateId, section, onUpdate, onDelete }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: action.id,
    data: { type: 'action-item', stateId, section },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const type = action.action || 'mqtt';

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`se2-action-row${isDragging ? ' se2-action-row--dragging' : ''}`}
    >
      {/* Drag handle */}
      <button
        className="se2-drag-handle"
        {...attributes}
        {...listeners}
        tabIndex={-1}
        title="Presunúť"
        type="button"
      >
        <GripVertical size={13} />
      </button>

      {/* Type badge - click cycles mqtt->audio->video->image */}
      <button
        className={`se2-action-badge se2-action-badge--${type}`}
        onClick={() => onUpdate(nextTypePatch(action))}
        title="Klikni pre zmenu typu"
        type="button"
      >
        {TYPE_LABELS[type] ?? type.toUpperCase()}
      </button>

      {/* Topic - only for mqtt */}
      {type === 'mqtt' && (
        <input
          className="se2-action-input se2-action-input--topic"
          value={action.topic || ''}
          onChange={(e) => onUpdate({ topic: e.target.value })}
          placeholder="room1/device/id"
          spellCheck={false}
        />
      )}

      {/* Message / command */}
      <input
        className="se2-action-input se2-action-input--message"
        value={action.message || ''}
        onChange={(e) => onUpdate({ message: e.target.value })}
        placeholder={
          type === 'audio' ? 'PLAY:file.wav:1.0' :
          type === 'video' ? 'PLAY_VIDEO:file.mp4' :
          type === 'image' ? 'SHOW:wallpaper.png | CLEAR' :
          'ON:50:L | OFF | SPEED:80 | DIR:L'
        }
        spellCheck={false}
      />

      <Button
        variant="ghost"
        size="small"
        icon={Trash2}
        cooldown={0}
        onClick={onDelete}
        className="se2-row-delete"
        title="Odstrániť"
      />
    </div>
  );
}

/** Renders onEnter or onExit action list for one state, with drag-to-reorder */
export default function ActionListEditor({ stateId, section, actions, onAdd, onUpdate, onDelete }) {
  const { setNodeRef, isOver } = useDroppable({
    id: `dropzone:${stateId}:${section}`,
    data: { type: 'action-item', stateId, section },
  });

  return (
    <div
      ref={setNodeRef}
      className={`se2-action-list${isOver ? ' se2-action-list--over' : ''}`}
    >
      {actions.length === 0 && (
        <p className="se2-empty-hint">Žiadne akcie.</p>
      )}

      <SortableContext
        items={actions.map((a) => a.id)}
        strategy={verticalListSortingStrategy}
      >
        {actions.map((action) => (
          <SortableActionRow
            key={action.id}
            action={action}
            stateId={stateId}
            section={section}
            onUpdate={(partial) => onUpdate(stateId, section, action.id, partial)}
            onDelete={() => onDelete(stateId, section, action.id)}
          />
        ))}
      </SortableContext>

      <Button
        variant="ghost"
        size="small"
        icon={Plus}
        cooldown={0}
        onClick={() => onAdd(stateId, section, createEmptyAction())}
        className="se2-add-btn"
      >
        Pridať akciu
      </Button>
    </div>
  );
}
