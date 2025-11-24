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
    // Tu by sme mohli vyhodiť event na odhlásenie, ak vyprší session
    throw new Error('Unauthorized');
  }
  return res;
};

export const api = {

  /* ===================================================================
     1. PRODUKČNÁ VERZIA LOGINU (PRE RASPBERRY PI)
     Až budeš na ostrom systéme:
     1. ODKOMENTUJ túto funkciu nižšie
     2. ZMAŽ tú "DEV VERZIU" pod ňou
  ===================================================================
  */
  
  /*
  login: async (username, password) => {
    const token = 'Basic ' + btoa(username + ':' + password);
    // Skúsime zavolať reálny backend na overenie hesla
    const res = await fetch(`${API_URL}/status`, {
        headers: { 'Authorization': token }
    });

    if (res.ok) {
        return token; // Heslo je správne, vrátime token
    } else {
        throw new Error('Nesprávne meno alebo heslo');
    }
  },
  */


  /* ===================================================================
     2. DEV VERZIA LOGINU (TERAZ AKTÍVNA)
     Použi toto, kým nemáš spustený Python backend.
     Meno: admin
     Heslo: 123
  ===================================================================
  */
  login: async (username, password) => {
    // Tieto údaje fungujú pre "offline" vývoj
    const DEV_USER = 'admin';
    const DEV_PASS = '123';

    console.log("⚠️ Používam FALOŠNÝ login (Dev Mode) - Python server asi nebeží.");
    
    // Simulácia čakania (akože komunikujeme so serverom)
    await new Promise(resolve => setTimeout(resolve, 600));

    if (username === DEV_USER && password === DEV_PASS) {
        // Vygenerujeme token, aby si aplikácia myslela, že sme prihlásení
        return 'Basic ' + btoa(username + ':' + password);
    }
    
    throw new Error('Zlé meno alebo heslo (Dev Mode: skús admin / 123)');
  },


  // ===================================================================
  // ZVYŠNÉ API VOLANIA (Tie už používajú reálny alebo proxy server)
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

  getSceneProgress: async () => {
    const res = await authFetch(`${API_URL}/scene/progress`);
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