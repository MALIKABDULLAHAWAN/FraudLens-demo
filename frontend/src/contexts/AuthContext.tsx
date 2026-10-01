import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';

interface AuthContextValue {
  token: string | null;
  role: string | null;
  email: string | null;
  setAuth: (token: string, role: string, email: string) => void;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem('role'));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem('email'));

  const setAuth = useCallback((t: string, r: string, e: string) => {
    localStorage.setItem('token', t);
    localStorage.setItem('role', r);
    localStorage.setItem('email', e);
    setToken(t);
    setRole(r);
    setEmail(e);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('email');
    setToken(null);
    setRole(null);
    setEmail(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, role, email, setAuth, logout, isAdmin: role === 'admin' }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
