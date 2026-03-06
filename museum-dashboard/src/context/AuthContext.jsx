import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
      if (import.meta.env.DEV) {
          setIsAuthenticated(true);
          setIsLoading(false);
          localStorage.setItem('auth_header', 'Basic DEV_MODE');
          return;
      }
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