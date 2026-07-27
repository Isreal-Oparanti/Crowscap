"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { getSession, clearSession, isSessionExpired } from "./session";
import { setTokenProvider, getToken } from "@/api/client";
import type { MobileSessionResponse } from "@/types/api";

interface AuthContextValue {
  session: MobileSessionResponse | null;
  isLoading: boolean;
  signOut: () => Promise<void>;
  setSession: (s: MobileSessionResponse) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = useState<MobileSessionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Wire up the token provider for the API client
    setTokenProvider(getToken);

    getSession().then((stored) => {
      if (stored && !isSessionExpired(stored)) {
        setSessionState(stored);
      }
      setIsLoading(false);
    });
  }, []);

  function setSession(s: MobileSessionResponse) {
    setSessionState(s);
  }

  async function signOut() {
    await clearSession();
    setSessionState(null);
  }

  return (
    <AuthContext.Provider value={{ session, isLoading, signOut, setSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used inside AuthProvider");
  return ctx;
}
