import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Save, Plus, Trash2, Wand2, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { useSceneEditor } from '../../hooks/useSceneEditor';
import Button from '../ui/Button';
import StatePanel from './StatePanel';
import '../../styles/views/scene-editor-v2.css';

export default function SceneEditorView() {
  const { sceneName } = useParams();

  const {
    initialState,
    states,
    selectedStateId,
    selectedState,
    isDirty,
    isSaving,
    selectState,
    addState,
    deleteState,
    renameState,
    updateState,
    updateMetadata,
    addAction,
    updateAction,
    deleteAction,
    addTransition,
    updateTransition,
    deleteTransition,
    saveToBackend,
    resetFromSchema,
  } = useSceneEditor({ sceneName });

  const [isLoading, setIsLoading] = useState(false);

  // Fetch scene from Pi whenever sceneName changes
  useEffect(() => {
    if (!sceneName) return;
    let cancelled = false;
    setIsLoading(true);
    api.getSceneContent(sceneName)
      .then((data) => { if (!cancelled) resetFromSchema(data); })
      .catch(() => { /* keep default/localStorage state on error */ })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [sceneName]); // eslint-disable-line react-hooks/exhaustive-deps

  const setInitialState = (name) => updateMetadata({ initialState: name });

  const handleSave = async () => {
    try {
      await saveToBackend();
      toast.success('Scéna uložená na Pi');
    } catch (err) {
      toast.error(err.message || 'Chyba pri ukladaní');
    }
  };

  return (
    <div className="se2-view">

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="se2-header">
        <div className="se2-header-left">
          <Wand2 size={18} className="se2-header-icon" />
          <span className="se2-header-title">Editor scén</span>
          {sceneName && <span className="file-badge">{sceneName}</span>}
          {isDirty && <span className="se2-dirty-badge">● neuložené</span>}
        </div>
        <Button
          variant="primary"
          icon={Save}
          onClick={handleSave}
          disabled={!isDirty || !sceneName}
          loading={isSaving}
          size="small"
        >
          Uložiť na Pi
        </Button>
      </div>

      {/* ── 3-panel body ───────────────────────────────────────── */}
      <div className={`se2-body${isLoading ? ' se2-body--loading' : ''}`}>
        {isLoading && (
          <div className="se2-loading-overlay">
            <Loader2 size={32} className="se2-loading-spinner" />
            <span>Načítavam scénu z Pi…</span>
          </div>
        )}

        {/* Panel 1 — State List */}
        <aside className="se2-state-list">
          <div className="se2-panel-header">
            <span className="se2-panel-label">Stavy</span>
            <Button
              variant="ghost"
              size="small"
              icon={Plus}
              onClick={addState}
              title="Pridať stav"
              cooldown={0}
            />
          </div>
          <ul className="se2-state-items">
            {states.map((state) => (
              <li
                key={state.id}
                className={`se2-state-item${selectedStateId === state.id ? ' active' : ''}`}
                onClick={() => selectState(state.id)}
              >
                <span className="se2-state-name">
                  {initialState === state.name && (
                    <span className="se2-initial-dot" title="Počiatočný stav">▶</span>
                  )}
                  {state.name}
                </span>
                <Button
                  variant="ghost"
                  size="small"
                  icon={Trash2}
                  cooldown={0}
                  disabled={states.length <= 1}
                  onClick={(e) => { e.stopPropagation(); deleteState(state.id); }}
                  className="se2-delete-btn"
                  title="Vymazať stav"
                />
              </li>
            ))}
          </ul>
        </aside>

        {/* Panel 2 — State detail */}
        <main className="se2-main">
          {selectedState ? (
            <StatePanel
              state={selectedState}
              allStates={states}
              initialState={initialState}
              onRename={renameState}
              onUpdateState={updateState}
              onSetInitial={setInitialState}
              onAddAction={addAction}
              onUpdateAction={updateAction}
              onDeleteAction={deleteAction}
              onAddTransition={addTransition}
              onUpdateTransition={updateTransition}
              onDeleteTransition={deleteTransition}
            />
          ) : (
            <div className="se2-placeholder">
              <p className="se2-placeholder-hint">Vyber stav z ľavého panela.</p>
            </div>
          )}
        </main>

        {/* Panel 3 — Palette (placeholder) */}
        <aside className="se2-palette">
          <div className="se2-panel-header">
            <span className="se2-panel-label">Paleta</span>
          </div>
          <div className="se2-placeholder se2-placeholder--sm">
            <p className="se2-placeholder-hint">Zariadenia a médiá prídu v ďalšej iterácii.</p>
          </div>
        </aside>

      </div>{/* end se2-body */}
    </div>
  );
}
