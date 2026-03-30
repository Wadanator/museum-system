import { useEffect, useState } from 'react';
import { api } from '../services/api';
import toast from 'react-hot-toast';
import { AuthContext } from './AuthContextValue';

export function AuthProvider({ children }) {
  const isDevMode = import.meta.env.DEV;
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => isDevMode || Boolean(localStorage.getItem('auth_header')),
  );
  const [isLoading] = useState(false);

  useEffect(() => {
      if (isDevMode) {
          localStorage.setItem('auth_header', 'Basic DEV_MODE');
      }
  }, [isDevMode]);

  const login = async (username, password) => {
    try {
      const token = await api.login(username, password);
      localStorage.setItem('auth_header', token);
      setIsAuthenticated(true);
      toast.success("Vitajte v systéme");
      return true;
    } catch (error) {
      console.error(error);
      toast.error(error?.message || "Zlé heslo alebo meno");
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
