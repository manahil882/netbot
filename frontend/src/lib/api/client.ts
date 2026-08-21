import { API_BASE_URL, ApiError, parseError } from "@/lib/api/config";
import { readAccessToken } from "@/lib/auth";

type RequestOptions = RequestInit & { auth?: boolean };

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const nextHeaders = new Headers(headers);

  if (auth) {
    const token = readAccessToken();
    if (token) nextHeaders.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: nextHeaders,
    signal: options.signal ?? AbortSignal.timeout(35_000),
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiForm<T>(
  path: string,
  form: FormData,
  options: { auth?: boolean; method?: string; timeoutMs?: number } = {},
): Promise<T> {
  const { auth = true, method = "POST", timeoutMs } = options;
  const headers = new Headers();
  if (auth) {
    const token = readAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: form,
    signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  return response.json() as Promise<T>;
}

export async function apiCheckEmailAvailable(email: string): Promise<boolean> {
  const response = await fetch(
    `${API_BASE_URL}/auth/check-email?email=${encodeURIComponent(email.trim().toLowerCase())}`,
  );
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  const data = (await response.json()) as { available: boolean };
  return data.available;
}

export async function apiSendVerificationCode(email: string) {
  const form = new FormData();
  form.set("email", email.trim().toLowerCase());
  const response = await fetch(`${API_BASE_URL}/auth/send-code`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  return response.json() as Promise<{
    ok: boolean;
    email: string;
    expires_in_minutes: number;
    dev_code?: string;
  }>;
}

export async function apiVerifyEmailCode(email: string, code: string) {
  const form = new FormData();
  form.set("email", email.trim().toLowerCase());
  form.set("code", code.trim());
  const response = await fetch(`${API_BASE_URL}/auth/verify-code`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  return response.json() as Promise<{ ok: boolean; email: string; email_token: string }>;
}

export async function apiLogin(email: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  return response.json() as Promise<{
    access_token: string;
    user_id: string;
    name: string;
    email: string;
    face_enrolled?: boolean;
  }>;
}

export async function apiRegister(
  name: string,
  email: string,
  password: string,
  emailToken: string,
  faceImage?: Blob | null,
) {
  const form = new FormData();
  form.set("name", name);
  form.set("email", email);
  form.set("password", password);
  form.set("email_token", emailToken);
  if (faceImage) form.set("face_image", faceImage, "face.jpg");

  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  return response.json() as Promise<{
    access_token: string;
    user_id: string;
    name: string;
    email: string;
    face_enrolled?: boolean;
  }>;
}

export async function apiFaceLogin(email: string, faceImage: Blob) {
  const form = new FormData();
  form.set("email", email);
  form.set("face_image", faceImage, "face.jpg");

  const response = await fetch(`${API_BASE_URL}/auth/face-login`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  return response.json() as Promise<{
    access_token: string;
    user_id: string;
    name: string;
    email: string;
    face_enrolled?: boolean;
  }>;
}

export async function apiFaceEnroll(faceImage: Blob) {
  const form = new FormData();
  form.set("face_image", faceImage, "face.jpg");
  return apiForm<{ status: string; face_enrolled?: boolean }>("/auth/face-enroll", form);
}

export async function apiUpdateProfile(name: string) {
  const form = new FormData();
  form.set("name", name);
  return apiForm<{ id: string; name: string; email: string; face_enrolled: boolean }>(
    "/auth/me",
    form,
    { method: "PATCH" },
  );
}

export async function apiDeleteAccount() {
  await apiFetch<void>("/auth/me", { method: "DELETE" });
}
