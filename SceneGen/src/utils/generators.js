import { ACTION_TYPES, TRANSITION_TYPES, DEFAULTS } from './constants';

/**
 * Generate unique ID for state/action/transition
 */
export const generateId = () => {
  return `id_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Create empty state object
 */
export const createEmptyState = (name = DEFAULTS.STATE_NAME) => ({
  id: generateId(),
  name: name,
  description: '',
  onEnter: [],
  onExit: [],
  timeline: [],
  transitions: []
});

/**
 * Create empty transition object
 */
export const createEmptyTransition = () => ({
  id: generateId(),
  type: TRANSITION_TYPES.TIMEOUT,
  delay: DEFAULTS.DELAY,
  goto: ''
});

/**
 * Create empty action object (mqtt only!)
 */
export const createEmptyAction = (type = ACTION_TYPES.MQTT) => {
  return {
    id: generateId(),
    action: ACTION_TYPES.MQTT,
    topic: '',
    message: ''
  };
};

/**
 * Create empty timeline item
 */
export const createEmptyTimelineItem = () => ({
  id: generateId(),
  at: DEFAULTS.TIMELINE_AT,
  ...createEmptyAction()
});