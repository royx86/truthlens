import React, { createContext, useContext, useState, useEffect } from 'react';
import { loginApi, signupApi, getMeApi, logoutApi } from '../services/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'truthlens_auth_token';
const USER_KEY = 'truthlens_auth_user';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(USER_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);

  // Sync / validate session on initial mount
  useEffect(() => {
    let isMounted = true;

    async function verifySession() {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      if (!savedToken) {
        if (isMounted) setIsLoading(false);
        return;
      }

      try {
        const freshUser = await getMeApi(savedToken);
        if (isMounted) {
          setUser(freshUser);
          localStorage.setItem(USER_KEY, JSON.stringify(freshUser));
        }
      } catch (err) {
        // Token was invalid or expired
        if (isMounted) {
          setToken(null);
          setUser(null);
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(USER_KEY);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    verifySession();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email, password) => {
    const data = await loginApi({ email, password });
    const { user: authUser, access_token } = data;

    setToken(access_token);
    setUser(authUser);
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(authUser));
    return data;
  };

  const signup = async (name, email, password) => {
    const data = await signupApi({ name, email, password });
    const { user: authUser, access_token } = data;

    setToken(access_token);
    setUser(authUser);
    localStorage.setItem(TOKEN_KEY, access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(authUser));
    return data;
  };

  const logout = async () => {
    try {
      await logoutApi();
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
