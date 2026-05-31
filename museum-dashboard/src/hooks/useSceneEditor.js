import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

// -- ID generation ------------------------------------------------------------

const generateId = () => `id_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// -- Factory functions (exported for use in components) ------------------------

export const createEmptyAction = (type = 'mqtt') => ({
  id: generateId(),
  action: type,
  topic: '',
  message: '',
});

export const createEmptyTimelineItem = (at = 0) => ({
  id: generateId(),
  at,
  action: 'mqtt',
  topic: '',
  message: '',
});

export const createEmptyTransition = () => ({
  id: generateId(),
  type: 'timeout',
  delay: 10,
  goto: '',
});

export const createEmptyState = (name = 'NEW_STATE') => ({
  id: generateId(),
  name,
  description: '',
  onEnter: [],
  onExit: [],
  timeline: [],
  transitions: [],
});

// -- Schema <-> internal format conversion --------------------------------------
// Internal format attaches `id` to every element for stable React keys.
// Schema format (what the Pi validates) has no `id` fields.

const withId = (obj) => ({ ...obj, id: generateId() });

export const schemaToInternal = (schemaJson) => {
  const states = Object.entries(schemaJson.states || {}).map(([name, s]) => ({
    id: generateId(),
    name,
    description: s.description || '',
    onEnter: (s.onEnter || []).map(withId),
    onExit: (s.onExit || []).map(withId),
    // Multi-action timeline items (actions[]) get exploded into separate clips at the same `at`
    timeline: (s.timeline || []).flatMap((item) =>
      item.actions
        ? item.actions.map((a) => ({ ...withId(a), at: item.at }))
        : [withId(item)]
    ),
    transitions: (s.transitions || []).map(withId),
  }));

  return {
    sceneId: schemaJson.sceneId || '',
    description: schemaJson.description || '',
    version: schemaJson.version || '2.0',
    initialState: schemaJson.initialState || states[0]?.name || '',
    globalEvents: (schemaJson.globalEvents || []).map(withId),
    states,
  };
};

const stripId = ({ id, ...rest }) => rest;

const cleanTransition = (t) => {
  const { id, ...rest } = t;
  switch (rest.type) {
    case 'timeout':
      return { type: rest.type, delay: Number(rest.delay), goto: rest.goto };
    case 'mqttMessage':
      return { type: rest.type, topic: rest.topic, message: rest.message, goto: rest.goto };
    case 'audioEnd':
    case 'videoEnd':
      return { type: rest.type, target: rest.target, goto: rest.goto };
    default:
      return rest;
  }
};

export const internalToSchema = (editor) => {
  const statesObj = {};

  editor.states.forEach((state) => {
    const s = {};
    if (state.description) s.description = state.description;
    if (state.onEnter?.length) s.onEnter = state.onEnter.map(stripId);
    if (state.timeline?.length) {
      s.timeline = [...state.timeline]
        .sort((a, b) => a.at - b.at)
        .map(({ id, ...rest }) => ({ ...rest, at: Number(rest.at) }));
    }
    if (state.onExit?.length) s.onExit = state.onExit.map(stripId);
    if (state.transitions?.length) s.transitions = state.transitions.map(cleanTransition);
    statesObj[state.name] = s;
  });

  return {
    sceneId: editor.sceneId,
    ...(editor.description ? { description: editor.description } : {}),
    ...(editor.version ? { version: editor.version } : {}),
    initialState: editor.initialState,
    ...(editor.globalEvents?.length ? { globalEvents: editor.globalEvents.map(cleanTransition) } : {}),
    states: statesObj,
  };
};

// -- LocalStorage recovery -----------------------------------------------------

const formatValidationError = (validation) => {
  const first = validation?.errors?.[0];
  if (!first) return 'Scena nie je validna';
  return `Scena nie je validna (${first.path}): ${first.message}`;
};

const storageKey = (sceneName) => `scene_editor_v2_${sceneName}`;

const saveToStorage = (sceneName, data) => {
  try {
    localStorage.setItem(storageKey(sceneName), JSON.stringify(data));
  } catch {
    // Quota exceeded - silently ignore
  }
};

const loadFromStorage = (sceneName) => {
  try {
    const raw = localStorage.getItem(storageKey(sceneName));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

// -- Hook ---------------------------------------------------------------------

const buildInitialEditor = (sceneName, initialData) => {
  if (sceneName) {
    const recovered = loadFromStorage(sceneName);
    if (recovered) return recovered;
  }
  if (initialData) return schemaToInternal(initialData);

  const firstState = createEmptyState('INTRO');
  return {
    sceneId: 'nova_scena',
    description: '',
    version: '2.0',
    initialState: 'INTRO',
    globalEvents: [],
    states: [firstState],
  };
};

export const useSceneEditor = ({ sceneName, initialData } = {}) => {
  const [editor, setEditor] = useState(() => buildInitialEditor(sceneName, initialData));
  const [selectedStateId, setSelectedStateId] = useState(() => editor.states[0]?.id ?? null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  // Auto-save to localStorage for crash recovery
  useEffect(() => {
    if (sceneName) saveToStorage(sceneName, editor);
    setIsDirty(true);
  }, [editor, sceneName]);

  // -- Internal updater ------------------------------------------------------

  const update = useCallback((fn) => setEditor((prev) => fn(prev)), []);

  // -- Metadata --------------------------------------------------------------

  const updateMetadata = useCallback(
    (partial) => update((prev) => ({ ...prev, ...partial })),
    [update]
  );

  // -- State selection -------------------------------------------------------

  const selectState = useCallback((id) => setSelectedStateId(id), []);

  const selectedState = editor.states.find((s) => s.id === selectedStateId) ?? null;

  // -- State CRUD ------------------------------------------------------------

  const addState = useCallback(() => {
    const newState = createEmptyState(`STATE_${Date.now().toString(36).toUpperCase()}`);
    update((prev) => ({
      ...prev,
      states: [...prev.states, newState],
      initialState: prev.initialState || newState.name,
    }));
    setSelectedStateId(newState.id);
    return newState.id;
  }, [update]);

  const deleteState = useCallback((id) => {
    update((prev) => {
      if (prev.states.length <= 1) return prev;
      const target = prev.states.find((s) => s.id === id);
      if (!target) return prev;

      const remaining = prev.states.filter((s) => s.id !== id);
      const newInitial =
        prev.initialState === target.name ? (remaining[0]?.name ?? '') : prev.initialState;

      // Remove transitions pointing at the deleted state
      const cleaned = remaining.map((s) => ({
        ...s,
        transitions: s.transitions.filter((t) => t.goto !== target.name),
      }));

      return { ...prev, states: cleaned, initialState: newInitial };
    });
    setSelectedStateId((prev) => (prev === id ? null : prev));
  }, [update]);

  // Renames a state and propagates the new name to all goto references across the whole scene
  const renameState = useCallback((id, newName) => {
    update((prev) => {
      const target = prev.states.find((s) => s.id === id);
      if (!target || target.name === newName) return prev;
      const oldName = target.name;

      const states = prev.states.map((s) => {
        const updatedTransitions = s.transitions.map((t) =>
          t.goto === oldName ? { ...t, goto: newName } : t
        );
        return s.id === id
          ? { ...s, name: newName, transitions: updatedTransitions }
          : { ...s, transitions: updatedTransitions };
      });

      const globalEvents = prev.globalEvents.map((e) =>
        e.goto === oldName ? { ...e, goto: newName } : e
      );

      const initialState = prev.initialState === oldName ? newName : prev.initialState;

      return { ...prev, states, globalEvents, initialState };
    });
  }, [update]);

  const updateState = useCallback((id, partial) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) => (s.id === id ? { ...s, ...partial } : s)),
    }));
  }, [update]);

  const reorderStates = useCallback((fromIndex, toIndex) => {
    update((prev) => {
      const states = [...prev.states];
      const [moved] = states.splice(fromIndex, 1);
      states.splice(toIndex, 0, moved);
      return { ...prev, states };
    });
  }, [update]);

  // -- onEnter / onExit action lists -----------------------------------------

  const addAction = useCallback((stateId, section, action = createEmptyAction()) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId ? { ...s, [section]: [...s[section], action] } : s
      ),
    }));
  }, [update]);

  const updateAction = useCallback((stateId, section, actionId, partial) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId
          ? {
              ...s,
              [section]: s[section].map((a) => (a.id === actionId ? { ...a, ...partial } : a)),
            }
          : s
      ),
    }));
  }, [update]);

  const deleteAction = useCallback((stateId, section, actionId) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId
          ? { ...s, [section]: s[section].filter((a) => a.id !== actionId) }
          : s
      ),
    }));
  }, [update]);

  const reorderActions = useCallback((stateId, section, fromIndex, toIndex) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) => {
        if (s.id !== stateId) return s;
        const items = [...s[section]];
        const [moved] = items.splice(fromIndex, 1);
        items.splice(toIndex, 0, moved);
        return { ...s, [section]: items };
      }),
    }));
  }, [update]);

  // -- Timeline --------------------------------------------------------------

  const addTimelineItem = useCallback((stateId, item = createEmptyTimelineItem()) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId ? { ...s, timeline: [...s.timeline, item] } : s
      ),
    }));
  }, [update]);

  const updateTimelineItem = useCallback((stateId, itemId, partial) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId
          ? {
              ...s,
              timeline: s.timeline.map((item) =>
                item.id === itemId ? { ...item, ...partial } : item
              ),
            }
          : s
      ),
    }));
  }, [update]);

  const deleteTimelineItem = useCallback((stateId, itemId) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId
          ? { ...s, timeline: s.timeline.filter((item) => item.id !== itemId) }
          : s
      ),
    }));
  }, [update]);

  // Third arg is either a bare number (from drag) or a partial object {at, message, topic, …} (from popover)
  const moveTimelineItem = useCallback((stateId, itemId, atOrPartial) => {
    const partial = typeof atOrPartial === 'number'
      ? { at: Math.max(0, +atOrPartial.toFixed(2)) }
      : atOrPartial;
    updateTimelineItem(stateId, itemId, partial);
  }, [updateTimelineItem]);

  // -- Transitions -----------------------------------------------------------

  const addTransition = useCallback((stateId, transition = createEmptyTransition()) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId ? { ...s, transitions: [...s.transitions, transition] } : s
      ),
    }));
  }, [update]);

  const updateTransition = useCallback((stateId, transId, partial) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId
          ? {
              ...s,
              transitions: s.transitions.map((t) =>
                t.id === transId ? { ...t, ...partial } : t
              ),
            }
          : s
      ),
    }));
  }, [update]);

  const deleteTransition = useCallback((stateId, transId) => {
    update((prev) => ({
      ...prev,
      states: prev.states.map((s) =>
        s.id === stateId
          ? { ...s, transitions: s.transitions.filter((t) => t.id !== transId) }
          : s
      ),
    }));
  }, [update]);

  // -- Global events ---------------------------------------------------------

  const setGlobalEvents = useCallback(
    (events) => update((prev) => ({ ...prev, globalEvents: events })),
    [update]
  );

  // -- Import / Export -------------------------------------------------------

  const exportJSON = useCallback(
    () => JSON.stringify(internalToSchema(editor), null, 2),
    [editor]
  );

  const importFromJSON = useCallback((jsonString) => {
    const parsed = typeof jsonString === 'string' ? JSON.parse(jsonString) : jsonString;
    const converted = schemaToInternal(parsed);
    setEditor(converted);
    setSelectedStateId(converted.states[0]?.id ?? null);
    setIsDirty(true);
  }, []);

  // -- Backend persistence ---------------------------------------------------

  const saveToBackend = useCallback(async (targetSceneName) => {
    const name = targetSceneName || sceneName;
    if (!name) throw new Error('Nie je zadané meno scény');
    const scenePayload = internalToSchema(editor);

    setIsSaving(true);
    try {
      const validation = await api.validateScene(scenePayload);
      if (!validation.valid) {
        const error = new Error(formatValidationError(validation));
        error.validation = validation;
        throw error;
      }

      await api.saveScene(name, scenePayload);
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  }, [editor, sceneName]);

  const clearRecovery = useCallback(() => {
    if (sceneName) localStorage.removeItem(storageKey(sceneName));
  }, [sceneName]);

  // Replaces the entire editor state from a Pi schema object (used on load)
  const resetFromSchema = useCallback((schemaJson) => {
    const next = schemaToInternal(schemaJson);
    if (sceneName) localStorage.removeItem(storageKey(sceneName));
    setEditor(next);
    setSelectedStateId(next.states[0]?.id ?? null);
    setIsDirty(false);
  }, [sceneName]);

  return {
    // Metadata
    sceneId: editor.sceneId,
    description: editor.description,
    version: editor.version,
    initialState: editor.initialState,
    globalEvents: editor.globalEvents,

    // States
    states: editor.states,
    selectedStateId,
    selectedState,

    // State ops
    selectState,
    addState,
    deleteState,
    renameState,
    updateState,
    reorderStates,
    updateMetadata,

    // Action ops (onEnter / onExit)
    addAction,
    updateAction,
    deleteAction,
    reorderActions,

    // Timeline ops
    addTimelineItem,
    updateTimelineItem,
    deleteTimelineItem,
    moveTimelineItem,

    // Transition ops
    addTransition,
    updateTransition,
    deleteTransition,

    // Global events
    setGlobalEvents,

    // Import / Export / Save
    exportJSON,
    importFromJSON,
    saveToBackend,
    clearRecovery,
    resetFromSchema,

    // Status
    isDirty,
    isSaving,
  };
};
