import { useState, useEffect } from 'react';
import ActionListEditor from './ActionListEditor';
import TransitionEditor from './TransitionEditor';

function SectionHeader({ label }) {
  return <div className="se2-section-header"><span>{label}</span></div>;
}

/**
 * StatePanel — center panel content for the selected state.
 * Metadata form + onEnter + onExit + transitions.
 */
export default function StatePanel({
  state,
  allStates,
  initialState,
  onRename,
  onUpdateState,
  onSetInitial,
  onAddAction,
  onUpdateAction,
  onDeleteAction,
  onReorderAction,
  onAddTransition,
  onUpdateTransition,
  onDeleteTransition,
}) {
  // Local name input — commit rename only on blur to avoid re-render on every keystroke
  const [nameInput, setNameInput] = useState(state.name);

  useEffect(() => {
    setNameInput(state.name);
  }, [state.id, state.name]);

  const handleNameBlur = () => {
    const trimmed = nameInput.trim().toUpperCase().replace(/[^A-Z0-9_]/g, '_');
    if (trimmed && trimmed !== state.name) {
      onRename(state.id, trimmed);
    } else {
      setNameInput(state.name);
    }
  };

  return (
    <div className="se2-state-panel">

      {/* ── Metadata ─────────────────────────────────────────── */}
      <div className="se2-meta-form">
        <div className="se2-meta-row">
          <label className="se2-meta-label">Názov stavu</label>
          <input
            className="se2-meta-input se2-meta-input--name"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value.toUpperCase())}
            onBlur={handleNameBlur}
            onKeyDown={(e) => e.key === 'Enter' && e.target.blur()}
            spellCheck={false}
          />
          <label className="se2-initial-toggle" title="Nastaviť ako počiatočný stav">
            <input
              type="checkbox"
              checked={initialState === state.name}
              onChange={() => onSetInitial(state.name)}
            />
            <span>Počiatočný</span>
          </label>
        </div>

        <div className="se2-meta-row">
          <label className="se2-meta-label">Popis</label>
          <input
            className="se2-meta-input"
            value={state.description || ''}
            onChange={(e) => onUpdateState(state.id, { description: e.target.value })}
            placeholder="Voliteľný popis stavu..."
          />
        </div>
      </div>

      {/* ── onEnter ──────────────────────────────────────────── */}
      <SectionHeader label="onEnter" />
      <ActionListEditor
        stateId={state.id}
        section="onEnter"
        actions={state.onEnter}
        onAdd={onAddAction}
        onUpdate={onUpdateAction}
        onDelete={onDeleteAction}
        onReorder={onReorderAction}
      />

      {/* ── onExit ───────────────────────────────────────────── */}
      <SectionHeader label="onExit" />
      <ActionListEditor
        stateId={state.id}
        section="onExit"
        actions={state.onExit}
        onAdd={onAddAction}
        onUpdate={onUpdateAction}
        onDelete={onDeleteAction}
        onReorder={onReorderAction}
      />

      {/* ── Transitions ──────────────────────────────────────── */}
      <SectionHeader label="Prechody" />
      <TransitionEditor
        stateId={state.id}
        transitions={state.transitions}
        allStates={allStates}
        onAdd={onAddTransition}
        onUpdate={onUpdateTransition}
        onDelete={onDeleteTransition}
      />

    </div>
  );
}
