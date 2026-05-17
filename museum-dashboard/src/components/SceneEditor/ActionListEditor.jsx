import { Plus, Trash2 } from 'lucide-react';
import Button from '../ui/Button';
import { createEmptyAction } from '../../hooks/useSceneEditor';

const TYPE_LABELS = { mqtt: 'MQTT', audio: 'AUDIO', video: 'VIDEO' };
const TYPE_CYCLE  = { mqtt: 'audio', audio: 'video', video: 'mqtt' };

/** Single inline-editable action row */
function ActionRow({ action, onUpdate, onDelete }) {
  const type = action.action || 'mqtt';

  return (
    <div className="se2-action-row">
      {/* Type badge — click cycles mqtt→audio→video */}
      <button
        className={`se2-action-badge se2-action-badge--${type}`}
        onClick={() => onUpdate({ action: TYPE_CYCLE[type] })}
        title="Klikni pre zmenu typu"
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

/** Renders onEnter or onExit action list for one state */
export default function ActionListEditor({ stateId, section, actions, onAdd, onUpdate, onDelete }) {
  return (
    <div className="se2-action-list">
      {actions.length === 0 && (
        <p className="se2-empty-hint">Žiadne akcie.</p>
      )}

      {actions.map((action) => (
        <ActionRow
          key={action.id}
          action={action}
          onUpdate={(partial) => onUpdate(stateId, section, action.id, partial)}
          onDelete={() => onDelete(stateId, section, action.id)}
        />
      ))}

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
