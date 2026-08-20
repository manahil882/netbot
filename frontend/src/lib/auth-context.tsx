"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  migrateAuthStorage,
  readAccessToken,
  readFaceEnrolled,
  readStoredAccount,
  readStoredAuth,
  writeAccessToken,
  writeFaceEnrolled,
  writeStoredAccount,
  writeStoredAuth,
  clearAccountData,
  type StoredAccount,
} from "@/lib/auth";

type AuthContextValue = {
  authed: boolean;
  ready: boolean;
  account: StoredAccount | null;
  faceEnrolled: boolean;
  login: () => void;
  logout: () => void;
  registerAccount: (account: StoredAccount) => void;
  setSession: (token: string, account: StoredAccount, faceEnrolled?: boolean) => void;
  markFaceEnrolled: () => void;
  deleteAccount: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(false);
  const [account, setAccount] = useState<StoredAccount | null>(null);
  const [faceEnrolled, setFaceEnrolled] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    migrateAuthStorage();
    setAuthed(readStoredAuth() && Boolean(readAccessToken()));
    setAccount(readStoredAccount());
    setFaceEnrolled(readFaceEnrolled());
    setReady(true);
  }, []);

  const login = useCallback(() => {
    writeStoredAuth(true);
    setAuthed(true);
  }, []);

  const logout = useCallback(() => {
    writeStoredAuth(false);
    writeAccessToken(null);
    setAuthed(false);
  }, []);

  const registerAccount = useCallback((next: StoredAccount) => {
    writeStoredAccount(next);
    setAccount(next);
    writeFaceEnrolled(false);
    setFaceEnrolled(false);
  }, []);

  const setSession = useCallback((token: string, next: StoredAccount, enrolled = true) => {
    writeAccessToken(token);
    writeStoredAccount(next);
    writeStoredAuth(true);
    writeFaceEnrolled(enrolled);
    setAccount(next);
    setAuthed(true);
    setFaceEnrolled(enrolled);
  }, []);

  const markFaceEnrolled = useCallback(() => {
    writeFaceEnrolled(true);
    setFaceEnrolled(true);
  }, []);

  const deleteAccount = useCallback(() => {
    clearAccountData();
    setAuthed(false);
    setAccount(null);
    setFaceEnrolled(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        authed,
        ready,
        account,
        faceEnrolled,
        login,
        logout,
        registerAccount,
        setSession,
        markFaceEnrolled,
        deleteAccount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
