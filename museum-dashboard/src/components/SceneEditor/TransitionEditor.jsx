import { Plus, Trash2 } from 'lucide-react';
import Button from '../ui/Button';
import { createEmptyTransition } from '../../hooks/useSceneEditor';

const TRANSITION_TYPES = [
  { value: 'timeout',     label: 'Timeout' },
  { value: 'mqttMessage', label: 'MQTT správa' },
  { value: 'audioEnd',    label: 'Koniec audia' },
  { value: 'videoEnd',    label: 'Koniec videa' },
  { value: 'always',      label: '-> Vždy' },
];

function TransitionRow({ trans, allStates, onUpdate, onDelete }) {
  const type = trans.type || 'timeout';

  const handleTypeChange = (newType) => {
    const base = { type: newType, goto: trans.goto };
    if (newType === 'timeout')          onUpdate({ ...base, delay: trans.delay ?? 10 });
    else if (newType === 'mqttMessage') onUpdate({ ...base, topic: trans.topic || '', message: trans.message || '' });
    else if (newType === 'audioEnd' || newType === 'videoEnd') onUpdate({ ...base, target: trans.target || '' });
    else                                onUpdate(base);
  };

  return (
    <div className="se2-transition-row">
      <div className="se2-transition-header">
        <select
          className="se2-select"
          value={type}
          onChange={(e) => handleTypeChange(e.target.value)}
        >
          {TRANSITION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        <select
          className="se2-select se2-select--goto"
          value={trans.goto || ''}
          onChange={(e) => onUpdate({ goto: e.target.value })}
        >
          <option value="">- goto -</option>
          {allStates.map((s) => (
            <option key={s.id} value={s.name}>{s.name}</option>
          ))}
          <option value="END">END</option>
        </select>

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

      {type === 'timeout' && (
        <div className="se2-transition-params">
          <label className="se2-param-label">Delay (s)</label>
          <input
            type="number"
            className="se2-action-input"
            min="0"
            step="0.5"
            value={trans.delay ?? 10}
            onChange={(e) => onUpdate({ delay: parseFloat(e.target.value) || 0 })}
          />
        </div>
      )}

      {type === 'mqttMessage' && (
        <div className="se2-transition-params">
          <input
            className="se2-action-input se2-action-input--topic"
            value={trans.topic || ''}
            onChange={(e) => onUpdate({ topic: e.target.value })}
            placeholder="room1/button1"
            spellCheck={false}
          />
          <input
            className="se2-action-input se2-action-input--message"
            value={trans.message || ''}
            onChange={(e) => onUpdate({ message: e.target.value })}
            placeholder="PRESSED"
            spellCheck={false}
          />
        </div>
      )}

      {(type === 'audioEnd' || type === 'videoEnd') && (
        <div className="se2-transition-params">
          <input
            className="se2-action-input"
            value={trans.target || ''}
            onChange={(e) => onUpdate({ target: e.target.value })}
            placeholder={type === 'audioEnd' ? 'intro.wav' : 'intro.mp4'}
            spellCheck={false}
          />
        </div>
      )}
    </div>
  );
}

export default function TransitionEditor({ stateId, transitions, allStates, onAdd, onUpdate, onDelete }) {
  return (
    <div className="se2-action-list">
      {transitions.length === 0 && (
        <p className="se2-empty-hint">Žiadne prechody.</p>
      )}

      {transitions.map((trans) => (
        <TransitionRow
          key={trans.id}
          trans={trans}
          allStates={allStates}
          onUpdate={(partial) => onUpdate(stateId, trans.id, partial)}
          onDelete={() => onDelete(stateId, trans.id)}
        />
      ))}

      <Button
        variant="ghost"
        size="small"
        icon={Plus}
        cooldown={0}
        onClick={() => onAdd(stateId, createEmptyTransition())}
        className="se2-add-btn"
      >
        Pridať prechod
      </Button>
    </div>
  );
}
