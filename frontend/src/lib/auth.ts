export const AUTH_KEY = "netbot-authenticated";
export const ACCOUNT_KEY = "netbot-account";
export const TOKEN_KEY = "netbot-access-token";
export const FACE_KEY = "netbot-face-enrolled";
const LEGACY_KEY = AUTH_KEY;

export type StoredAccount = {
  name: string;
  email: string;
  password?: string;
  userId?: string;
};

function getStorage() {
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

/** Drop old localStorage auth so a fresh visit always starts at the intro. */
export function migrateAuthStorage() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(LEGACY_KEY);
  } catch {
    // Ignore.
  }
}

export function readStoredAuth(): boolean {
  const storage = getStorage();
  if (!storage) return false;
  try {
    return storage.getItem(AUTH_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeStoredAuth(value: boolean) {
  const storage = getStorage();
  if (!storage) return;
  try {
    if (value) storage.setItem(AUTH_KEY, "1");
    else {
      storage.removeItem(AUTH_KEY);
      storage.removeItem(TOKEN_KEY);
    }
  } catch {
    // Storage may be blocked in private mode; in-memory auth still applies.
  }
}

export function readAccessToken(): string | null {
  const storage = getStorage();
  if (!storage) return null;
  try {
    return storage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeAccessToken(token: string | null) {
  const storage = getStorage();
  if (!storage) return;
  try {
    if (token) storage.setItem(TOKEN_KEY, token);
    else storage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore.
  }
}

export function readStoredAccount(): StoredAccount | null {
  const storage = getStorage();
  if (!storage) return null;
  try {
    const raw = storage.getItem(ACCOUNT_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredAccount;
  } catch {
    return null;
  }
}

export function writeStoredAccount(account: StoredAccount) {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(ACCOUNT_KEY, JSON.stringify(account));
  } catch {
    // Ignore.
  }
}

export function readFaceEnrolled(): boolean {
  const storage = getStorage();
  if (!storage) return false;
  try {
    return storage.getItem(FACE_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeFaceEnrolled(value: boolean) {
  const storage = getStorage();
  if (!storage) return;
  try {
    if (value) storage.setItem(FACE_KEY, "1");
    else storage.removeItem(FACE_KEY);
  } catch {
    // Ignore.
  }
}

export function clearAccountData() {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.removeItem(ACCOUNT_KEY);
    storage.removeItem(FACE_KEY);
    storage.removeItem(AUTH_KEY);
    storage.removeItem(TOKEN_KEY);
  } catch {
    // Ignore.
  }
}

/** @deprecated Use useAuth() from auth-context instead. */
export function isAuthenticated(): boolean {
  return readStoredAuth();
}

export type PasswordStrength = {
  score: number;
  label: "Too weak" | "Weak" | "Fair" | "Good" | "Strong";
  percent: number;
};

export function getPasswordStrength(password: string): PasswordStrength {
  if (!password) {
    return { score: 0, label: "Too weak", percent: 0 };
  }

  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  const capped = Math.min(score, 4);
  const labels: PasswordStrength["label"][] = ["Too weak", "Weak", "Fair", "Good", "Strong"];

  return {
    score: capped,
    label: labels[capped],
    percent: capped * 25,
  };
}

export function isStrongPassword(password: string): boolean {
  return getPasswordStrength(password).score >= 3 && password.length >= 8;
}

export function accountInitials(account: StoredAccount | null): string {
  const name = account?.name?.trim() ?? "";
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  if (parts[0]) return parts[0][0].toUpperCase();
  const email = account?.email?.trim() ?? "";
  return (email[0] ?? "N").toUpperCase();
}

export function accountFirstName(account: StoredAccount | null): string {
  const name = account?.name?.trim() ?? "";
  return name.split(/\s+/).filter(Boolean)[0] || "You";
}
