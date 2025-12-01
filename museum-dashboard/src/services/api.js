const API_URL = '/api';

// Pomocná funkcia na získanie hlavičiek (Authorization)
const getHeaders = () => {
  const headers = {};
  const auth = localStorage.getItem('auth_header');
  if (auth) {
    headers['Authorization'] = auth;
  }
  return headers;
};

// Wrapper pre fetch, ktorý automaticky pridáva auth hlavičky
export const authFetch = async (url, options = {}) => {
  const headers = getHeaders();
  
  // Ak body nie je FormData (napr. posielame JSON), pridáme Content-Type.
  // Pri FormData (upload súborov) to prehliadač nastaví automaticky.
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const finalOptions = {
    ...options,
    headers: {
      ...headers,
      ...options.headers
    }
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
    // Skúsime zavolať backend na overenie hesla
    const res = await fetch(`${API_URL}/status`, {
        headers: { 'Authorization': token }
    });

    if (res.ok) {
        return token;
    } else {
        throw new Error('Nesprávne meno alebo heslo');
    }
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

  // Logy a systém
  clearLogs: async () => {
    const res = await authFetch(`${API_URL}/logs/clear`, { method: 'POST' });
    return res.json();
  },

  restartSystem: async () => {
    const res = await authFetch(`${API_URL}/system/restart`, { method: 'POST' });
    return res.json();
  },

  restartService: async () => {
    const res = await authFetch(`${API_URL}/system/service/restart`, { method: 'POST' });
    return res.json();
  }
};