import { generateId } from './generators';

/**
 * Remove ID fields from objects for clean JSON export
 */
const stripIds = (obj) => {
  const { id, ...rest } = obj;
  return rest;
};

/**
 * Clean transition object - remove unnecessary fields based on type
 */
const cleanTransition = (trans) => {
  const base = { type: trans.type };
  
  switch (trans.type) {
    case 'timeout':
      return { ...base, delay: trans.delay, goto: trans.goto };
    
    case 'mqttMessage':
      return { ...base, topic: trans.topic, message: trans.message, goto: trans.goto };
    
    case 'audioEnd':
      return { ...base, target: trans.target, goto: trans.goto };
    
    case 'videoEnd':
      return { ...base, target: trans.target, goto: trans.goto };
    
    default:
      return stripIds(trans);
  }
};

/**
 * Clean action object - remove ID only
 */
const cleanAction = (action) => {
  return stripIds(action);
};

/**
 * Generate JSON in state machine format
 */
export const generateStateMachineJSON = (sceneId, description, version, initialState, states, globalEvents = []) => {
  const statesObject = {};
  
  states.forEach(state => {
    const stateData = {
      description: state.description || ''
    };

    // Add onEnter if exists
    if (state.onEnter?.length > 0) {
      stateData.onEnter = state.onEnter.map(cleanAction);
    }

    // Add timeline if exists
    if (state.timeline?.length > 0) {
      stateData.timeline = state.timeline.map(item => {
        const cleaned = cleanAction(item);
        return cleaned;
      });
    }

    // Add onExit if exists
    if (state.onExit?.length > 0) {
      stateData.onExit = state.onExit.map(cleanAction);
    }

    // Add transitions if exists
    if (state.transitions?.length > 0) {
      stateData.transitions = state.transitions.map(cleanTransition);
    }

    statesObject[state.name] = stateData;
  });

  const json = {
    sceneId,
    description,
    version,
    initialState: initialState || states[0]?.name || '',
    states: statesObject
  };

  // Add globalEvents if they exist
  if (globalEvents && globalEvents.length > 0) {
    json.globalEvents = globalEvents.map(cleanTransition);
  }

  return json;
};

/**
 * Format JSON with indentation
 */
export const formatJSON = (data) => {
  return JSON.stringify(data, null, 2);
};

/**
 * Download JSON file
 */
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

/**
 * Import JSON and convert to internal format
 */
export const importJSON = (jsonData) => {
  const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
  
  const sceneId = data.sceneId || 'imported_scene';
  const description = data.description || '';
  const version = data.version || '2.0';
  const initialState = data.initialState || '';
  
  // Extract global prefix from first MQTT topic if available
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