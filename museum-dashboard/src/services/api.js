const API_URL = '/api';

const getHeaders = () => {
  const headers = {};
  const auth = localStorage.getItem('auth_header');
  if (auth) {
    headers['Authorization'] = auth;
  }
  return headers;
};

export const authFetch = async (url, options = {}) => {
  const headers = getHeaders();
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const finalOptions = {
    ...options,
    headers: { ...headers, ...options.headers }
  };
  const res = await fetch(url, finalOptions);
  if (res.status === 401) {
    throw new Error('Unauthorized');
  }
  return res;
};

export const api = {
  login: async (username, password) => {
    const token = 'Basic ' + btoa(username + ':' + password);
    const res = await fetch(`${API_URL}/status`, {
        headers: { 'Authorization': token }
    });
    if (res.ok) return token;
    else throw new Error('Nesprávne meno alebo heslo');
  },

  getStatus: async () => {
    const res = await authFetch(`${API_URL}/status`);
    return res.json();
  },

  getScenes: async () => {
    const res = await authFetch(`${API_URL}/scenes`);
    return res.json();
  },

  getSceneContent: async (sceneName) => {
    const res = await authFetch(`${API_URL}/scene/${sceneName}`);
    return res.json();
  },

  saveScene: async (sceneName, data) => {
    const res = await authFetch(`${API_URL}/scene/${sceneName}`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
    return res.json();
  },

  runScene: async (sceneName) => {
    const res = await authFetch(`${API_URL}/run_scene/${sceneName}`, { method: 'POST' });
    return res.json();
  },

  stopScene: async () => {
    const res = await authFetch(`${API_URL}/stop_scene`, { method: 'POST' });
    return res.json();
  },

  // --- COMMANDS & DEVICES ---

  getCommands: async () => {
    const res = await authFetch(`${API_URL}/commands`);
    return res.json();
  },

  getCommandContent: async (commandName) => {
    const res = await authFetch(`${API_URL}/command/${commandName}`);
    return res.json();
  },

  saveCommand: async (commandName, data) => {
    const res = await authFetch(`${API_URL}/command/${commandName}`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
    return res.json();
  },

  runCommand: async (commandName) => {
    const res = await authFetch(`${API_URL}/run_command/${commandName}`, { method: 'POST' });
    return res.json();
  },

  getDevices: async () => {
    const res = await authFetch(`${API_URL}/devices`);
    return res.json();
  },

  // NOVÉ: Priame odoslanie MQTT správy
  sendMqtt: async (topic, message) => {
    const res = await authFetch(`${API_URL}/mqtt/send`, {
      method: 'POST',
      body: JSON.stringify({ topic, message })
    });
    return res.json();
  },

  // --- LOGY A SYSTÉM ---

  clearLogs: async () => {
    const res = await authFetch(`${API_URL}/logs/clear`, { method: 'POST' });
    return res.json();
  },

  restartSystem: async () => {
    const res = await authFetch(`${API_URL}/system/restart`, { method: 'POST' });
    return res.json();
  }
};