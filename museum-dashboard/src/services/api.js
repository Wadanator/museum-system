// Súbor: museum-dashboard/src/services/api.js (Zmenený)
const API_URL = '/api';

// Pomocná funkcia na získanie hlavičiek (Authorization)
const getHeaders = () => {
  const headers = { 'Content-Type': 'application/json' };
  const auth = localStorage.getItem('auth_header'); // Načítame token z prehliadača
  if (auth) {
    headers['Authorization'] = auth;
  }
  return headers;
};

// Wrapper pre fetch, ktorý automaticky pridáva auth hlavičky
const authFetch = async (url, options = {}) => {
  const res = await fetch(url, { ...options, headers: getHeaders() });
  
  if (res.status === 401) {
    // Ak vyprší session alebo je zlé heslo, vyhodíme chybu
    throw new Error('Unauthorized');
  }
  return res;
};

export const api = {

  /* ===================================================================
     PRODUKČNÝ LOGIN (Overenie voči RPi Backend)
  =================================================================== */
  login: async (username, password) => {
    // Vytvoríme Basic Auth token
    const token = 'Basic ' + btoa(username + ':' + password);
    
    // Skúsime zavolať reálny backend na overenie hesla.
    // Endpoint /status je chránený (@requires_auth), takže ak prejde, heslo je správne.
    const res = await fetch(`${API_URL}/status`, {
        headers: { 'Authorization': token }
    });

    if (res.ok) {
        return token; // Heslo je správne, vrátime token
    } else {
        throw new Error('Nesprávne meno alebo heslo');
    }
  },

  // ===================================================================
  // ZVYŠNÉ API VOLANIA
  // ===================================================================

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

  // ZMENA: Funkcia getSceneProgress bola odstránená, nahrádza ju Socket.IO push.
  // getSceneProgress: async () => {
  //   const res = await authFetch(`${API_URL}/scene/progress`);
  //   return res.json();
  // },

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