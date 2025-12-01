import { generateId } from './generators';
import { TRANSITION_TYPES } from './constants';

const stripIds = (obj) => {
  // eslint-disable-next-line no-unused-vars
  const { id, ...rest } = obj;
  return rest;
};

const cleanTransition = (trans) => {
  // RPI používa 'mqttMessage' aj pre tlačidlá
  const type = trans.type === TRANSITION_TYPES.BUTTON_PRESS ? TRANSITION_TYPES.MQTT_MESSAGE : trans.type;
  const base = { type };
  
  switch (type) {
    case TRANSITION_TYPES.TIMEOUT:
      return { ...base, delay: Number(trans.delay), goto: trans.goto };
    
    case TRANSITION_TYPES.MQTT_MESSAGE:
      return { ...base, topic: trans.topic, message: trans.message, goto: trans.goto };
    
    case TRANSITION_TYPES.AUDIO_END:
      return { ...base, target: trans.target, goto: trans.goto };
    
    case TRANSITION_TYPES.VIDEO_END:
      return { ...base, target: trans.target, goto: trans.goto };
    
    default:
      return stripIds(trans);
  }
};

const cleanAction = (action) => {
  return stripIds(action);
};

export const generateStateMachineJSON = (sceneId, description, version, initialState, states, globalEvents = []) => {
  const statesObject = {};
  
  states.forEach(state => {
    const stateData = {
      description: state.description || ''
    };

    if (state.onEnter?.length > 0) {
      stateData.onEnter = state.onEnter.map(cleanAction);
    }

    if (state.timeline?.length > 0) {
      stateData.timeline = state.timeline.map(item => {
        const cleaned = cleanAction(item);
        return {
          at: Number(item.at), 
          ...cleaned
        };
      });
    }

    if (state.onExit?.length > 0) {
      stateData.onExit = state.onExit.map(cleanAction);
    }

    if (state.transitions?.length > 0) {
      stateData.transitions = state.transitions.map(cleanTransition);
    }

    statesObject[state.name] = stateData;
  });

  const json = {
    sceneId,
    description: description || "",
    version,
    initialState: initialState || states[0]?.name || '',
    
    // --- GLOBAL EVENTS EXPORT ---
    // Pridáme len ak existujú
    ...(globalEvents && globalEvents.length > 0 
        ? { globalEvents: globalEvents.map(cleanTransition) } 
        : {}),

    states: statesObject
  };

  return json;
};

export const formatJSON = (data) => {
  return JSON.stringify(data, null, 2);
};

export const downloadJSON = (data, filename) => {
  const json = formatJSON(data);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.json') ? filename : `${filename}.json`;
  a.click();
  URL.revokeObjectURL(url);
};

export const importJSON = (jsonData) => {
  const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
  
  const sceneId = data.sceneId || 'imported_scene';
  const description = data.description || '';
  const version = data.version || '2.0';
  const initialState = data.initialState || '';
  
  // Skúsime uhádnuť prefix z prvej akcie
  let globalPrefix = 'room1';
  const firstState = Object.values(data.states || {})[0];
  if (firstState?.onEnter?.[0]?.topic) {
    const parts = firstState.onEnter[0].topic.split('/');
    if (parts.length > 0) {
      globalPrefix = parts[0];
    }
  }

  const states = Object.entries(data.states || {}).map(([name, stateData]) => ({
    id: generateId(),
    name,
    description: stateData.description || '',
    onEnter: (stateData.onEnter || []).map(action => ({ 
      ...action, 
      id: generateId()
    })),
    onExit: (stateData.onExit || []).map(action => ({ 
      ...action, 
      id: generateId()
    })),
    timeline: (stateData.timeline || []).map(item => ({ 
      ...item, 
      id: generateId()
    })),
    transitions: (stateData.transitions || []).map(trans => ({
      ...trans, 
      id: generateId()
    }))
  }));

  // Import global events
  const globalEvents = (data.globalEvents || []).map(event => ({
    ...event,
    id: generateId()
  }));

  return {
    sceneId,
    description,
    version,
    initialState,
    states,
    globalEvents,
    globalPrefix
  };
};