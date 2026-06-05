// Action types - All actions are MQTT commands in this system.
export const ACTION_TYPES = {
  MQTT: 'mqtt',
  AUDIO: 'audio',
  VIDEO: 'video'
};

// Transition types
export const TRANSITION_TYPES = {
  TIMEOUT: 'timeout',
  MQTT_MESSAGE: 'mqttMessage',
  BUTTON_PRESS: 'buttonPress', // New dedicated transition type
  AUDIO_END: 'audioEnd',      
  VIDEO_END: 'videoEnd'
};

// Default values
export const DEFAULTS = {
  SCENE_ID: 'my_scene',
  DESCRIPTION: 'Scene description',
  VERSION: '2.0',
  STATE_NAME: 'new_state',
  GLOBAL_PREFIX: 'room1',
  DELAY: 1.0,
  TIMELINE_AT: 0
};

// MQTT Devices Configuration
export const MQTT_DEVICES = {
  // --- MOTORY ---
  motor1: {
    label: 'Kolesá (Motor 1)',
    type: 'motor',
    topicSuffix: 'motor1', // Prefix sa doplní automaticky (room1/motor1)
    defaultSpeed: 75,
    hasSpeed: true,
    hasDirection: true
  },
  motor2: {
    label: 'Hodiny (Motor 2)',
    type: 'motor',
    topicSuffix: 'motor2',
    defaultSpeed: 50,
    hasSpeed: true,
    hasDirection: true
  },

  // --- RELÁTKA A EFEKTY ---
  smoke_on: {
    label: 'Dymostroj ON (Power)',
    type: 'simple',
    topicSuffix: 'power/smoke_ON',
    commands: ['ON', 'OFF']
  },
  light_fire: {
    label: 'Svetlo Oheň',
    type: 'simple',
    topicSuffix: 'light/fire',
    commands: ['ON', 'OFF']
  },
  smoke_timed: {
    label: 'Dymostroj Časovaný (Effect)',
    type: 'simple',
    topicSuffix: 'effect/smoke',
    commands: ['ON', 'OFF']
  },
  light_1: {
    label: 'Svetlo 1',
    type: 'simple',
    topicSuffix: 'light/1',
    commands: ['ON', 'OFF']
  },
  light_2: {
    label: 'Svetlo 2',
    type: 'simple',
    topicSuffix: 'light/2',
    commands: ['ON', 'OFF']
  },
  light_3: {
    label: 'Svetlo 3',
    type: 'simple',
    topicSuffix: 'light/3',
    commands: ['ON', 'OFF']
  },
  light_4: {
    label: 'Svetlo 4',
    type: 'simple',
    topicSuffix: 'light/4',
    commands: ['ON', 'OFF']
  },
  light_5: {
    label: 'Svetlo 5',
    type: 'simple',
    topicSuffix: 'light/5',
    commands: ['ON', 'OFF']
  },
  effects_group1: {
    label: 'Blikanie Budíky (Group 1)',
    type: 'simple',
    topicSuffix: 'effects/group1',
    commands: ['ON', 'OFF', 'BLINK']
  },
  effects_alone: {
    label: 'Blikanie 1 Žiarovka',
    type: 'simple',
    topicSuffix: 'effects/alone',
    commands: ['ON', 'OFF', 'BLINK']
  },

  // --- MULTIMÉDIA ---
  audio: {
    label: 'Audio Player',
    type: 'audio',
    info: 'For audio commands (e.g., PLAY:file.mp3:0.8)'
  },
  video: {
    label: 'Video Player',
    type: 'video',
    info: 'For video commands (e.g., PLAY_VIDEO:file.mp4)'
  }
};

// Colors for state visualization
export const STATE_COLORS = {
  ON_ENTER: 'green',
  ON_EXIT: 'orange',
  TIMELINE: 'blue',
  TRANSITION: 'purple'
};
