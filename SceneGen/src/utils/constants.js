// Action types - All actions are MQTT commands in this system.
export const ACTION_TYPES = {
  MQTT: 'mqtt'
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
  motor1: {
    label: 'Motor 1',
    type: 'motor',
    hasSpeed: true,
    hasDirection: true
  },
  motor2: {
    label: 'Motor 2',
    type: 'motor',
    hasSpeed: true,
    hasDirection: true
  },
  light: {
    label: 'Light',
    type: 'simple',
    commands: ['ON', 'OFF']
  },
  steam: {
    label: 'Steam/Smoke',
    type: 'simple',
    commands: ['ON', 'OFF']
  },
  smoke: {
    label: 'Smoke',
    type: 'simple',
    commands: ['ON', 'OFF']
  },
  button1_led: {
    label: 'Button 1 LED',
    type: 'simple',
    commands: ['ON', 'OFF', 'BLINK']
  },
  button2_led: {
    label: 'Button 2 LED',
    type: 'simple',
    commands: ['ON', 'OFF', 'BLINK']
  },
  audio: {
    label: '🎵 Audio Player',
    type: 'audio',
    info: 'For audio commands (e.g., PLAY:file.mp3:0.8)'
  },
  video: {
    label: '🎬 Video Player',
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