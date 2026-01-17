import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // 1. Zistíme, či bežíme v DEV móde na Windowse (localhost)
    // Týmto rozlíšime "Vývoj na PC" vs "Ostré RPi"
    const isLocalDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (isLocalDev) {
        console.log("🖥️ Localhost (Windows) detekovaný: Preskakujem login pre dizajn.");
        // Nastavíme, že sme prihlásení, aj keď nemáme server
        setIsAuthenticated(true);
        setIsLoading(false);
        // Uložíme dummy token, aby api.js nekričalo hneď (hoci requesty zlyhajú)
        localStorage.setItem('auth_header', 'Basic DEV_MODE');
        return;
    }

    // 2. Štandardná logika pre RPi (vyžaduje overenie)
    const storedAuth = localStorage.getItem('auth_header');
    if (storedAuth) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      const token = await api.login(username, password);
      localStorage.setItem('auth_header', token);
      setIsAuthenticated(true);
      toast.success("Vitajte v systéme");
      setTimeout(() => window.location.reload(), 500);
      return true;
    } catch (e) {
      toast.error("Nesprávne prihlasovacie údaje");
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_header');
    setIsAuthenticated(false);
    toast('Boli ste odhlásený', { icon: '👋' });
    // Na localhoste ťa to po refreshnutí znova prihlási, čo je pre dizajn žiadané
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);