import React, { createContext, useContext, useEffect, useState } from 'react';
import apiClient from '@/lib/api/client';
import type { User } from '@/types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string, role?: 'developer' | 'banking_staff') => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = 'contextfoundry_jwt';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Synchronize token with apiClient on boot and fetch current user profile
  useEffect(() => {
    const initializeAuth = async () => {
      const savedToken = localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!savedToken) {
        setIsLoading(false);
        return;
      }

      apiClient.setToken(savedToken);
      try {
        const profile = await apiClient.getCurrentUser();
        setUser(profile);
        setToken(savedToken);
      } catch (err) {
        console.warn('Session expired or invalid, clearing authentication token:', err);
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        apiClient.setToken(null);
        setUser(null);
        setToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiClient.login({ email, password });
    setUser(response.user);
    setToken(response.access_token);
    localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
    apiClient.setToken(response.access_token);
  };

  const signup = async (email: string, password: string, name: string, role?: 'developer' | 'banking_staff') => {
    const response = await apiClient.signup({ email, password, name, role });
    setUser(response.user);
    setToken(response.access_token);
    localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
    apiClient.setToken(response.access_token);
  };

  const logout = () => {
    apiClient.logout();
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
