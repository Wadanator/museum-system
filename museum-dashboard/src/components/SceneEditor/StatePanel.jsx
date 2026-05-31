import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Plus } from 'lucide-react';
import ActionListEditor from './ActionListEditor';
import TransitionEditor from './TransitionEditor';
import VisualTimeline from './VisualTimeline';

/**
 * SectionAccordion - collapsible section with a toggle header.
 * Header shows label, optional item count badge, and optional add button.
 */
function SectionAccordion({ label, count, isOpen, onToggle, onAdd, children }) {
  const Chevron = isOpen ? ChevronDown : ChevronRight;
  return (
    <div className="se2-section-accordion">
      <div
        className="se2-section-toggle"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onToggle()}
      >
        <div className="se2-section-toggle-left">
          <Chevron size={13} className="se2-section-chevron" />
          <span className="se2-section-label">{label}</span>
          {count > 0 && <span className="se2-section-count">{count}</span>}
        </div>
        {onAdd && (
          <button
            className="se2-section-add-btn"
            type="button"
            title={`Pridať do ${label}`}
            onClick={(e) => { e.stopPropagation(); onAdd(); }}
          >
            <Plus size={12} />
          </button>
        )}
      </div>
      {isOpen && <div className="se2-section-body">{children}</div>}
    </div>
  );
}

/**
 * StatePanel - center panel content for the selected state.
 * Section order: Metadata -> onEnter -> Timeline -> onExit -> Transitions
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
  onMoveTimelineItem,
  onCommitTimelineItem,
  onDeleteTimelineItem,
  onAddTransition,
  onUpdateTransition,
  onDeleteTransition,
}) {
  // Local name input - commit rename only on blur to avoid re-render on every keystroke
  const [nameInput, setNameInput] = useState(state.name);

  // Accordion open state - onEnter + Timeline open by default
  const [open, setOpen] = useState({ onEnter: true, timeline: true, onExit: false, transitions: false });

  useEffect(() => {
    setNameInput(state.name);
  }, [state.id, state.name]);

  // Reset accordion when switching to a different state
  useEffect(() => {
    setOpen({ onEnter: true, timeline: true, onExit: false, transitions: false });
  }, [state.id]);

  const toggle = (key) => setOpen((prev) => ({ ...prev, [key]: !prev[key] }));

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

      {/* -- Metadata ------------------------------------------- */}
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

      {/* -- onEnter -------------------------------------------- */}
      <SectionAccordion
        label="onEnter"
        count={state.onEnter.length}
        isOpen={open.onEnter}
        onToggle={() => toggle('onEnter')}
        onAdd={() => onAddAction(state.id, 'onEnter')}
      >
        <ActionListEditor
          stateId={state.id}
          section="onEnter"
          actions={state.onEnter}
          onAdd={onAddAction}
          onUpdate={onUpdateAction}
          onDelete={onDeleteAction}
        />
      </SectionAccordion>

      {/* -- Timeline ------------------------------------------- */}
      <SectionAccordion
        label="Timeline"
        count={state.timeline.length}
        isOpen={open.timeline}
        onToggle={() => toggle('timeline')}
      >
        <VisualTimeline
          stateId={state.id}
          timeline={state.timeline}
          onMove={onMoveTimelineItem}
          onCommit={onCommitTimelineItem}
          onDelete={onDeleteTimelineItem}
        />
      </SectionAccordion>

      {/* -- onExit --------------------------------------------- */}
      <SectionAccordion
        label="onExit"
        count={state.onExit.length}
        isOpen={open.onExit}
        onToggle={() => toggle('onExit')}
        onAdd={() => onAddAction(state.id, 'onExit')}
      >
        <ActionListEditor
          stateId={state.id}
          section="onExit"
          actions={state.onExit}
          onAdd={onAddAction}
          onUpdate={onUpdateAction}
          onDelete={onDeleteAction}
        />
      </SectionAccordion>

      {/* -- Transitions ---------------------------------------- */}
      <SectionAccordion
        label="Prechody"
        count={state.transitions.length}
        isOpen={open.transitions}
        onToggle={() => toggle('transitions')}
        onAdd={() => onAddTransition(state.id)}
      >
        <TransitionEditor
          stateId={state.id}
          transitions={state.transitions}
          allStates={allStates}
          onAdd={onAddTransition}
          onUpdate={onUpdateTransition}
          onDelete={onDeleteTransition}
        />
      </SectionAccordion>

    </div>
  );
}
