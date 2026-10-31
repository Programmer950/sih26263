import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';
import { UserSummary, LoginResponse, UserProfile } from '../types/auth';

interface AuthContextType {
  user: UserSummary | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<UserSummary>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSummary | null>(() => {
    const saved = localStorage.getItem('apaar_setu_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('apaar_setu_token');
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const verifySession = async () => {
      if (token) {
        try {
          const res = await api.get<UserProfile>('/auth/me');
          setUser({
            id: res.data.id,
            name: res.data.name,
            email: res.data.email,
            role: res.data.role as any,
            institution_id: res.data.institution_id,
            institution_name: res.data.institution_name,
            institution_code: res.data.institution_code,
          });
        } catch {
          // Token expired or revoked
          setUser(null);
          setToken(null);
          localStorage.removeItem('apaar_setu_token');
          localStorage.removeItem('apaar_setu_user');
        }
      }
      setIsLoading(false);
    };

    verifySession();
  }, [token]);

  const login = async (email: string, password: string): Promise<UserSummary> => {
    const response = await api.post<LoginResponse>('/auth/login', { email, password });
    const { access_token, user: loggedInUser } = response.data;

    setToken(access_token);
    setUser(loggedInUser);
    localStorage.setItem('apaar_setu_token', access_token);
    localStorage.setItem('apaar_setu_user', JSON.stringify(loggedInUser));

    return loggedInUser;
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (e) {
      console.warn('Logout call failed or already expired', e);
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem('apaar_setu_token');
      localStorage.removeItem('apaar_setu_user');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        isAuthenticated: !!user && !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

