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
  updateAccount: (patch: Partial<StoredAccount>) => void;
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
    clearAccountData();
    setAuthed(false);
    setAccount(null);
    setFaceEnrolled(false);
  }, []);

  const registerAccount = useCallback((next: StoredAccount) => {
    writeStoredAccount(next);
    setAccount(next);
    writeFaceEnrolled(false);
    setFaceEnrolled(false);
  }, []);

  const updateAccount = useCallback((patch: Partial<StoredAccount>) => {
    setAccount((prev) => {
      if (!prev) return prev;
      const next = { ...prev, ...patch };
      writeStoredAccount(next);
      return next;
    });
  }, []);

  const setSession = useCallback((token: string, next: StoredAccount, enrolled?: boolean) => {
    writeAccessToken(token);
    writeStoredAccount(next);
    writeStoredAuth(true);
    setAccount(next);
    setAuthed(true);
    if (enrolled !== undefined) {
      writeFaceEnrolled(enrolled);
      setFaceEnrolled(enrolled);
    } else {
      writeFaceEnrolled(false);
      setFaceEnrolled(false);
    }
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
        updateAccount,
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
