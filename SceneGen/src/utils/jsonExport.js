import { generateId } from './generators';
import { TRANSITION_TYPES } from './constants';

/**
 * Remove ID fields from objects for clean JSON export
 * @param {object} obj - The object to strip ID from.
 */
const stripIds = (obj) => {
  // eslint-disable-next-line no-unused-vars
  const { id, ...rest } = obj;
  return rest;
};

/**
 * Clean transition object - remove unnecessary fields based on type
 * NOTE: BUTTON_PRESS is exported as mqttMessage for RPI compatibility.
 * @param {object} trans - The raw transition object.
 */
const cleanTransition = (trans) => {
  // Convert BUTTON_PRESS type back to mqttMessage for RPI compatibility
  const type = trans.type === TRANSITION_TYPES.BUTTON_PRESS ? TRANSITION_TYPES.MQTT_MESSAGE : trans.type;
  const base = { type };
  
  switch (type) {
    case TRANSITION_TYPES.TIMEOUT:
      return { ...base, delay: trans.delay, goto: trans.goto };
    
    case TRANSITION_TYPES.MQTT_MESSAGE:
      return { ...base, topic: trans.topic, message: trans.message, goto: trans.goto };
    
    case TRANSITION_TYPES.AUDIO_END:
      return { ...base, target: trans.target, goto: trans.goto };
    
    case TRANSITION_TYPES.VIDEO_END:
      return { ...base, target: trans.target, goto: trans.goto };
    
    default:
      // Fallback for unknown/custom types
      return stripIds(trans);
  }
};

/**
 * Clean action object - remove ID only
 * @param {object} action - The raw action object.
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

    // Add timeline if exists (BUG FIX: Ensure 'at' property is preserved)
    if (state.timeline?.length > 0) {
      // Timeline items are actions with an 'at' property
      stateData.timeline = state.timeline.map(item => {
        const cleaned = cleanAction(item);
        return {
          at: item.at, // 'at' field is essential for timeline
          ...cleaned
        };
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
 * @param {object} data - The JSON data object.
 */
export const formatJSON = (data) => {
  return JSON.stringify(data, null, 2);
};

/**
 * Download JSON file
 * @param {object} data - The JSON data object.
 * @param {string} filename - The desired filename.
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
 * @param {string} jsonData - The JSON string data.
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
    // Ensure timeline items keep the 'at' property when generating IDs
    timeline: (stateData.timeline || []).map(item => ({ 
      ...item, 
      id: generateId()
    })),
    transitions: (stateData.transitions || []).map(trans => {
        // We map the incoming type directly. If it was a 'buttonPress' and was exported as 'mqttMessage', 
        // it comes back as 'mqttMessage', which the TransitionEditor UI handles via pattern matching for display.
        return {
          ...trans, 
          id: generateId()
        };
    })
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