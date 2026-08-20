import { apiFetch } from "@/lib/api/client";

export type ThreadSummary = {
  id: string;
  title: string;
  last_updated: string;
};

export type ApiMessage = {
  id: string;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type Citation = {
  source_filename: string;
  page_number: number;
  chunk_index: number;
  score: number;
  excerpt: string;
};

export type ChatResponse = {
  thread_id: string;
  answer: string;
  citations: Citation[];
  tools_used: string[];
};

export function listThreads() {
  return apiFetch<ThreadSummary[]>("/threads");
}

export function getThreadMessages(threadId: string) {
  return apiFetch<ApiMessage[]>(`/threads/${threadId}`);
}

export function createThread(title: string) {
  return apiFetch<{ id: string; title: string }>("/threads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function renameThread(threadId: string, title: string) {
  return apiFetch<{ id: string; title: string }>(`/threads/${threadId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function deleteThread(threadId: string) {
  return apiFetch<void>(`/threads/${threadId}`, { method: "DELETE" });
}

export type IndexedDocument = {
  filename: string;
  chunks: number;
  pages: number;
};

export function sendChat(message: string, threadId?: string) {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      thread_id: threadId ?? null,
    }),
    signal: AbortSignal.timeout(70_000),
  });
}

export async function uploadDocument(file: File, threadId: string) {
  const form = new FormData();
  form.set("file", file, file.name);
  form.set("thread_id", threadId);
  const { apiForm } = await import("@/lib/api/client");
  return apiForm<{ filename: string; chunks: number; pages: number }>(
    "/documents/upload",
    form,
    { timeoutMs: 120_000 },
  );
}

export function listDocuments(threadId: string) {
  return apiFetch<IndexedDocument[]>(`/documents?thread_id=${encodeURIComponent(threadId)}`);
}

export function deleteDocument(threadId: string, filename: string) {
  return apiFetch<{ status: string; filename: string }>(
    `/documents?thread_id=${encodeURIComponent(threadId)}&filename=${encodeURIComponent(filename)}`,
    { method: "DELETE" },
  );
}

export async function transcribeAudio(blob: Blob) {
  const form = new FormData();
  form.set("file", blob, "recording.webm");
  const { apiForm } = await import("@/lib/api/client");
  return apiForm<{ text: string }>("/voice/transcribe", form);
}

export async function speakText(text: string): Promise<Blob> {
  const { API_BASE_URL } = await import("@/lib/api/config");
  const { readAccessToken } = await import("@/lib/auth");
  const form = new FormData();
  form.set("text", text);
  const headers = new Headers();
  const token = readAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/voice/speak`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!response.ok) {
    const { parseError, ApiError } = await import("@/lib/api/config");
    throw new ApiError(await parseError(response), response.status);
  }
  return response.blob();
}
