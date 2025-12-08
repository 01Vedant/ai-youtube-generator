import React, { createContext, useContext, useEffect, useState } from 'react';
import type { AuthTokens, Me } from '../types/auth';
import { login as apiLogin, register as apiRegister, me as apiMe } from '../lib/api';

type AuthContextType = {
  user: Me | null;
  tokens: AuthTokens | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<Me | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem('auth_tokens');
    if (raw) {
      try {
        const t = JSON.parse(raw) as AuthTokens;
        setTokens(t);
        apiMe().then(setUser).catch(() => setUser(null));
      } catch {
        // ignore
      }
    }
  }, []);

  const login = async (email: string, password: string) => {
    const t = await apiLogin(email, password);
    setTokens(t);
    const u = await apiMe();
    setUser(u);
  };

  const register = async (email: string, password: string) => {
    const res = await apiRegister(email, password);
    if ('ok' in res && res.ok) {
      await login(email, password);
    } else {
      throw new Error((res as any).error || 'Register failed');
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_tokens');
    setTokens(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, tokens, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function usePlan(): { plan: 'free' | 'pro' } {
  const { user } = useAuth();
  const pid = user?.plan_id === 'pro' ? 'pro' : 'free';
  return { plan: pid };
}
