import { GripVertical, Plus, Trash2 } from 'lucide-react';
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import Button from '../ui/Button';
import { createEmptyAction } from '../../hooks/useSceneEditor';

const TYPE_LABELS = { mqtt: 'MQTT', audio: 'AUDIO', video: 'VIDEO' };
const TYPE_CYCLE  = { mqtt: 'audio', audio: 'video', video: 'mqtt' };

/** Single sortable action row with drag handle */
function SortableActionRow({ action, onUpdate, onDelete }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: action.id });

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

      {/* Type badge — click cycles mqtt→audio→video */}
      <button
        className={`se2-action-badge se2-action-badge--${type}`}
        onClick={() => onUpdate({ action: TYPE_CYCLE[type] })}
        title="Klikni pre zmenu typu"
        type="button"
      >
        {TYPE_LABELS[type]}
      </button>

      {/* Topic — only for mqtt */}
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
          'ON'
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
export default function ActionListEditor({
  stateId,
  section,
  actions,
  onAdd,
  onUpdate,
  onDelete,
  onReorder,
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  );

  const handleDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return;
    const oldIndex = actions.findIndex((a) => a.id === active.id);
    const newIndex = actions.findIndex((a) => a.id === over.id);
    if (oldIndex !== -1 && newIndex !== -1) {
      onReorder(stateId, section, oldIndex, newIndex);
    }
  };

  return (
    <div className="se2-action-list">
      {actions.length === 0 && (
        <p className="se2-empty-hint">Žiadne akcie.</p>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={actions.map((a) => a.id)}
          strategy={verticalListSortingStrategy}
        >
          {actions.map((action) => (
            <SortableActionRow
              key={action.id}
              action={action}
              onUpdate={(partial) => onUpdate(stateId, section, action.id, partial)}
              onDelete={() => onDelete(stateId, section, action.id)}
            />
          ))}
        </SortableContext>
      </DndContext>

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
