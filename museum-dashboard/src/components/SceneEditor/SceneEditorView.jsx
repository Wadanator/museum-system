import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { Save, Plus, Trash2, Wand2, Loader2, Play, Square } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  pointerWithin,
  rectIntersection,
} from '@dnd-kit/core';
import { api } from '../../services/api';
import { useSceneEditor, createEmptyAction, createEmptyTimelineItem } from '../../hooks/useSceneEditor';
import Button from '../ui/Button';
import PageHeader from '../ui/PageHeader';
import StatePanel from './StatePanel';
import EditorPalette from './EditorPalette';
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
    reorderActions,
    addTimelineItem,
    moveTimelineItem,
    deleteTimelineItem,
    addTransition,
    updateTransition,
    deleteTransition,
    saveToBackend,
    resetFromSchema,
  } = useSceneEditor({ sceneName });

  const [isLoading, setIsLoading] = useState(false);
  const [activeDragData, setActiveDragData] = useState(null);
  const [testingState, setTestingState] = useState(null); // { name } when a test run is active

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } })
  );

  // Palette items drag across panels — use pointer-based detection so distance
  // between panels doesn't fool closestCenter. Sortable reorder keeps closestCenter.
  const collisionDetection = (args) => {
    if (args.active.data?.current?.type === 'palette') {
      const hits = pointerWithin(args);
      return hits.length > 0 ? hits : rectIntersection(args);
    }
    return closestCenter(args);
  };

  const handleDragStart = ({ active }) => {
    setActiveDragData(active.data?.current ?? null);
  };

  const handleDragEnd = ({ active, over, delta, activatorEvent }) => {
    setActiveDragData(null);
    if (!over || active.id === over.id) return;

    const activeData = active.data?.current;
    const overData   = over.data?.current;

    if (activeData?.type === 'palette') {
      if (overData?.zone === 'timeline-track') {
        // Compute drop time from actual pointer position relative to track's left edge.
        // over.rect is a MutableRefObject<ClientRect> in dnd-kit v6.
        const trackRect = over.rect?.current ?? over.rect;
        const pps       = overData.pixelsPerSecond ?? 80;
        const pointerX  = (activatorEvent?.clientX ?? 0) + (delta?.x ?? 0);
        const relX      = trackRect ? Math.max(0, pointerX - trackRect.left) : 0;
        const at        = +(relX / pps).toFixed(2);

        const { stateId: tlStateId } = overData;
        const item = {
          ...createEmptyTimelineItem(at),
          action: activeData.actionType,
          ...(activeData.topic ? { topic: activeData.topic } : {}),
          message: activeData.message ?? '',
        };
        addTimelineItem(tlStateId, item);
        return;
      }

      // Palette item dropped onto an action list (onEnter / onExit)
      const targetStateId = overData?.stateId;
      const targetSection = overData?.section;
      if (!targetStateId || !targetSection) return;

      const action = {
        ...createEmptyAction(activeData.actionType),
        ...(activeData.topic ? { topic: activeData.topic } : {}),
        message: activeData.message,
      };
      addAction(targetStateId, targetSection, action);

    } else if (activeData?.type === 'action-item') {
      // Sortable reorder within the same list
      if (!overData?.stateId) return;
      if (activeData.stateId !== overData.stateId || activeData.section !== overData.section) return;

      const { stateId, section } = activeData;
      const targetState = states.find((s) => s.id === stateId);
      const actionList  = targetState?.[section] ?? [];
      const fromIdx = actionList.findIndex((a) => a.id === active.id);
      const toIdx   = actionList.findIndex((a) => a.id === over.id);
      if (fromIdx !== -1 && toIdx !== -1 && fromIdx !== toIdx) {
        reorderActions(stateId, section, fromIdx, toIdx);
      }
    }
  };

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

  // ── State test-run ────────────────────────────────────────────
  // Builds a minimal 1-state scene, saves it as __test__ on the Pi, and runs it.
  // Uses only existing api.saveScene + api.runScene — no Pi-side changes needed.

  const buildTestScene = (state) => {
    const stripId = ({ id, ...rest }) => rest;
    const maxAt = state.timeline.reduce((m, item) => Math.max(m, item.at), 0);
    const duration = Math.max(maxAt + 15, 30); // at least 30s, or timeline end + 15s buffer

    return {
      sceneId: '__test__',
      version: '2.0',
      initialState: state.name,
      states: {
        [state.name]: {
          ...(state.onEnter?.length  ? { onEnter:   state.onEnter.map(stripId)  } : {}),
          ...(state.timeline?.length ? { timeline:  [...state.timeline]
            .sort((a, b) => a.at - b.at)
            .map(({ id, ...r }) => ({ ...r, at: Number(r.at) })) } : {}),
          ...(state.onExit?.length   ? { onExit:    state.onExit.map(stripId)   } : {}),
          transitions: [{ type: 'timeout', delay: duration, goto: '__END__' }],
        },
        __END__: {},
      },
    };
  };

  const handleTestState = async (state) => {
    try {
      await api.saveScene('__test__', buildTestScene(state));
      await api.runScene('__test__');
      setTestingState({ name: state.name });
      toast.success(`▶ Testuje sa: ${state.name}`);
    } catch (err) {
      toast.error(err.message || 'Chyba pri spúšťaní testu');
    }
  };

  const handleStopTest = async () => {
    try {
      await api.stopScene();
    } catch {
      // ignore — best-effort stop
    }
    setTestingState(null);
  };

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
      <PageHeader
        title="Editor scén"
        subtitle={sceneName}
        icon={Wand2}
      >
        {isDirty && <span className="se2-dirty-badge">● neuložené</span>}
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
      </PageHeader>

      {/* ── Test-run banner ────────────────────────────────────── */}
      {testingState && (
        <div className="se2-test-banner">
          <span className="se2-test-banner-pulse" />
          <span className="se2-test-banner-text">Testuje sa stav <strong>{testingState.name}</strong> na Pi…</span>
          <button className="se2-test-banner-stop" type="button" onClick={handleStopTest}>
            <Square size={11} />
            Zastaviť
          </button>
        </div>
      )}

      {/* ── 3-panel body ───────────────────────────────────────── */}
      <DndContext
        sensors={sensors}
        collisionDetection={collisionDetection}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
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
                <div className="se2-state-actions">
                  <Button
                    variant="ghost"
                    size="small"
                    icon={testingState?.name === state.name ? Square : Play}
                    cooldown={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      testingState?.name === state.name
                        ? handleStopTest()
                        : handleTestState(state);
                    }}
                    className={`se2-test-btn${testingState?.name === state.name ? ' se2-test-btn--active' : ''}`}
                    title={testingState?.name === state.name ? 'Zastaviť test' : 'Otestovať stav na Pi'}
                  />
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
                </div>
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
              onMoveTimelineItem={moveTimelineItem}
              onCommitTimelineItem={moveTimelineItem}
              onDeleteTimelineItem={deleteTimelineItem}
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

        {/* Panel 3 — Palette */}
        <aside className="se2-palette">
          <div className="se2-panel-header">
            <span className="se2-panel-label">Paleta</span>
          </div>
          <EditorPalette
            selectedStateId={selectedStateId}
            onAddAction={addAction}
          />
        </aside>

      </div>{/* end se2-body */}

      <DragOverlay>
        {activeDragData?.type === 'palette' && (
          <div className="se2-drag-overlay-pill">
            {activeDragData.label}
          </div>
        )}
      </DragOverlay>
      </DndContext>
    </div>
  );
}
