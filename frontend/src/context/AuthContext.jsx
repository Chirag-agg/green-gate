import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getMe } from '../utils/api';

const AuthContext = createContext(null);

function clearSessionStorage() {
  localStorage.removeItem('greengate_token');
  localStorage.removeItem('greengate_user');
}

export function AuthProvider({ children }) {
  const [authLoading, setAuthLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  const syncFromStorage = useCallback(() => {
    const cachedUser = JSON.parse(localStorage.getItem('greengate_user') || 'null');
    setUser(cachedUser);
  }, []);

  const logout = useCallback(() => {
    clearSessionStorage();
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  const refreshSession = useCallback(async () => {
    const token = localStorage.getItem('greengate_token');
    if (!token) {
      setIsAuthenticated(false);
      setUser(null);
      setAuthLoading(false);
      return;
    }

    try {
      const res = await getMe();
      const me = res.data || {};
      const normalizedUser = {
        user_id: me.id,
        company_name: me.company_name,
        email: me.email,
      };
      localStorage.setItem('greengate_user', JSON.stringify(normalizedUser));
      setUser(normalizedUser);
      setIsAuthenticated(true);
    } catch (_err) {
      clearSessionStorage();
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, []);

  useEffect(() => {
    syncFromStorage();
    refreshSession();
  }, [refreshSession, syncFromStorage]);

  const value = useMemo(
    () => ({
      authLoading,
      isAuthenticated,
      user,
      refreshSession,
      logout,
    }),
    [authLoading, isAuthenticated, user, refreshSession, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
