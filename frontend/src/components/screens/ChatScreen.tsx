"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import ChatSidebar from "@/components/chat/ChatSidebar";
import Composer from "@/components/chat/Composer";
import MessageList from "@/components/chat/MessageList";
import SourcesRail from "@/components/chat/SourcesRail";
import SpeechControls from "@/components/chat/SpeechControls";
import {
  createThread,
  deleteDocument,
  deleteThread,
  getThreadMessages,
  listDocuments,
  listThreads,
  renameThread,
  sendChat,
  uploadDocument,
  type Citation,
  type IndexedDocument,
} from "@/lib/api/chat";
import { ApiError } from "@/lib/api/config";
import { type Conversation, type Message, type Source } from "@/lib/data";
import { useAuth } from "@/lib/auth-context";
import { useSidebar } from "@/lib/sidebar-context";
import { useSpeechSettings } from "@/lib/speech/useSpeechSettings";
import { useSpeaker } from "@/lib/useSpeech";

const NEW_CHAT_ID = "new-chat";
const PIN_KEY_PREFIX = "netbot.pinned.";

function citationsToSources(citations: Citation[]): Source[] {
  return citations.map((c, index) => ({
    id: `src-${c.source_filename}-${c.page_number}-${c.chunk_index}-${index}`,
    tag: "DOC",
    title: c.source_filename,
    blurb: c.excerpt || "",
    meta: `p.${c.page_number || "?"}`,
    match: Math.round(c.score * 100),
  }));
}

function formatCite(citations: Citation[]): string | undefined {
  const top = citations[0];
  if (!top) return undefined;
  return `${top.source_filename} · p.${top.page_number || "?"}`;
}

function emptyConversation(): Conversation {
  return {
    id: NEW_CHAT_ID,
    title: "New chat",
    group: "Today",
    subtitle: "Ask anything — answers are grounded on your documents",
    messages: [],
    sources: [],
  };
}

function readPinned(userId: string | undefined): string[] {
  if (!userId || typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(PIN_KEY_PREFIX + userId);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function writePinned(userId: string | undefined, ids: string[]) {
  if (!userId || typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PIN_KEY_PREFIX + userId, JSON.stringify(ids));
  } catch {
    // ignore
  }
}

export default function ChatScreen({ full = true }: { full?: boolean }) {
  const searchParams = useSearchParams();
  const { account } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([emptyConversation()]);
  const [activeId, setActiveId] = useState(NEW_CHAT_ID);
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);
  const [thinking, setThinking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [highlightedSourceId, setHighlightedSourceId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [attachName, setAttachName] = useState<string | null>(null);
  const [attachState, setAttachState] = useState<"uploading" | "ready" | "error" | null>(null);
  const [chatFiles, setChatFiles] = useState<IndexedDocument[]>([]);
  const [railOpen, setRailOpen] = useState(true);
  const { open: sidebarOpen, setOpen: setSidebarOpen } = useSidebar();
  const toastTimer = useRef<number | null>(null);

  const { settings } = useSpeechSettings();
  const { speakingId, speak, speakIfAutoRead, stop, isSpeaking } = useSpeaker(
    settings.autoReadReplies,
  );

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? conversations[0],
    [conversations, activeId],
  );

  const flash = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 2600);
  }, []);

  useEffect(() => {
    setPinnedIds(readPinned(account?.userId));
  }, [account?.userId]);

  const loadFiles = useCallback(async (threadId: string) => {
    if (!threadId || threadId === NEW_CHAT_ID) {
      setChatFiles([]);
      return;
    }
    try {
      setChatFiles(await listDocuments(threadId));
    } catch {
      setChatFiles([]);
    }
  }, []);

  useEffect(() => {
    void loadFiles(activeId);
  }, [activeId, loadFiles]);

  useEffect(() => {
    async function loadThreads() {
      try {
        const threads = await listThreads();
        const loaded = await Promise.all(
          threads.map(async (thread) => {
            const messages = await getThreadMessages(thread.id);
            return {
              id: thread.id,
              title: thread.title,
              group: "Recent",
              subtitle: "Grounded RAG chat",
              messages: messages.map(
                (m): Message => ({
                  id: m.id,
                  role: m.role === "assistant" ? "bot" : "user",
                  text: m.content,
                }),
              ),
              sources: [],
            } satisfies Conversation;
          }),
        );
        const next = loaded.length > 0 ? loaded : [emptyConversation()];
        setConversations(next);

        const sharedId = searchParams.get("c");
        if (sharedId && next.some((c) => c.id === sharedId)) {
          setActiveId(sharedId);
        } else {
          setActiveId(next[0]?.id ?? NEW_CHAT_ID);
        }
      } catch (err) {
        flash(err instanceof ApiError ? err.message : "Could not load conversations");
        setConversations([emptyConversation()]);
      } finally {
        setLoading(false);
      }
    }

    void loadThreads();
  }, [flash, searchParams]);

  const updateConversation = useCallback(
    (id: string, update: (conversation: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((c) => (c.id === id ? update(c) : c)));
    },
    [],
  );

  const handleSend = useCallback(
    async (text: string) => {
      if (!active) return;

      const userMessage: Message = { id: `u-${Date.now()}`, role: "user", text };
      const pendingId = `b-${Date.now()}`;
      const threadId = active.id === NEW_CHAT_ID ? undefined : active.id;

      updateConversation(active.id, (c) => ({
        ...c,
        messages: [...c.messages, userMessage, { id: pendingId, role: "bot", text: "", pending: true }],
      }));
      setThinking(true);

      try {
        const response = await sendChat(text, threadId);
        const sources = citationsToSources(response.citations);
        const cite = formatCite(response.citations);

        setConversations((prev) => {
          return prev.map((c) => {
            if (c.id !== active.id) return c;
            return {
              id: response.thread_id,
              title: c.title === "New chat" ? text.slice(0, 48) : c.title,
              group: c.group,
              subtitle:
                sources.length > 0
                  ? `Grounded on ${sources.length} document chunks`
                  : "No documents retrieved yet",
              messages: c.messages.map((m) =>
                m.id === pendingId
                  ? { id: pendingId, role: "bot" as const, text: response.answer, cite }
                  : m,
              ),
              sources,
            };
          });
        });

        if (active.id === NEW_CHAT_ID) {
          setActiveId(response.thread_id);
        }

        speakIfAutoRead(pendingId, response.answer);
      } catch (err) {
        updateConversation(active.id, (c) => ({
          ...c,
          messages: c.messages.filter((m) => m.id !== pendingId),
        }));
        const name = err instanceof Error ? err.name : "";
        const message =
          err instanceof ApiError
            ? err.message
            : name === "TimeoutError" || name === "AbortError"
              ? "The assistant timed out. Try again."
              : err instanceof TypeError
                ? "Cannot reach the backend at localhost:8000. Make sure it is running."
                : err instanceof Error
                  ? err.message
                  : "Could not send message";
        flash(message);
      } finally {
        setThinking(false);
      }
    },
    [active, updateConversation, speakIfAutoRead, flash],
  );

  const handleAttach = useCallback(
    async (file: File) => {
      setAttachName(file.name);
      setAttachState("uploading");
      flash(`Indexing ${file.name}… first time can take a minute`);
      try {
        let threadId = active.id === NEW_CHAT_ID ? "" : active.id;
        if (!threadId) {
          const created = await createThread(file.name.replace(/\.[^.]+$/, "") || "Documents");
          threadId = created.id;
          setConversations((prev) => {
            const rest = prev.filter((c) => c.id !== NEW_CHAT_ID);
            return [
              {
                ...emptyConversation(),
                id: threadId,
                title: created.title || file.name,
                subtitle: "Grounded RAG chat",
              },
              ...rest,
            ];
          });
          setActiveId(threadId);
        }
        const result = await uploadDocument(file, threadId);
        setAttachState("ready");
        await loadFiles(threadId);
        flash(`${result.filename} indexed (${result.chunks} chunks). Ask a question about it.`);
      } catch (err) {
        setAttachState("error");
        flash(err instanceof ApiError ? err.message : "Could not upload document");
      }
    },
    [active, flash, loadFiles],
  );

  const handleDeleteFile = useCallback(
    async (filename: string) => {
      if (active.id === NEW_CHAT_ID) return;
      try {
        await deleteDocument(active.id, filename);
        await loadFiles(active.id);
        updateConversation(active.id, (c) => ({
          ...c,
          sources: c.sources.filter((s) => s.title !== filename),
        }));
        flash(`Removed ${filename}`);
      } catch (err) {
        flash(err instanceof ApiError ? err.message : "Could not remove file");
      }
    },
    [active.id, flash, loadFiles, updateConversation],
  );

  const handleNewChat = useCallback(() => {
    const exists = conversations.some((c) => c.id === NEW_CHAT_ID);
    if (!exists) {
      setConversations((prev) => [emptyConversation(), ...prev]);
    }
    setActiveId(NEW_CHAT_ID);
  }, [conversations]);

  const handleRename = useCallback(
    async (id: string, title: string) => {
      if (id === NEW_CHAT_ID) {
        updateConversation(id, (c) => ({ ...c, title }));
        return;
      }
      try {
        const updated = await renameThread(id, title);
        updateConversation(id, (c) => ({ ...c, title: updated.title || title }));
        flash("Chat renamed");
      } catch (err) {
        flash(err instanceof ApiError ? err.message : "Could not rename chat");
      }
    },
    [flash, updateConversation],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      if (id !== NEW_CHAT_ID) {
        try {
          await deleteThread(id);
        } catch (err) {
          flash(err instanceof ApiError ? err.message : "Could not delete chat");
          return;
        }
      }
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (next.length === 0) return [emptyConversation()];
        if (id === activeId) setActiveId(next[0].id);
        return next;
      });
      setPinnedIds((prev) => prev.filter((p) => p !== id));
      flash("Chat deleted");
    },
    [activeId, flash],
  );

  const handleExport = useCallback(
    (id: string) => {
      const conversation = conversations.find((c) => c.id === id);
      if (!conversation) return;

      const blob = new Blob([JSON.stringify(conversation, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${conversation.id}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      flash("Exported as JSON");
    },
    [conversations, flash],
  );

  const handleShare = useCallback(
    async (id: string) => {
      const link = `${window.location.origin}/chat?c=${id}`;
      try {
        await navigator.clipboard.writeText(link);
        flash("Share link copied");
      } catch {
        flash(link);
      }
    },
    [flash],
  );

  const handleSpeak = useCallback(
    (message: Message) => {
      speak(message.id, message.text);
    },
    [speak],
  );

  const handleCiteClick = useCallback(
    (cite: string) => {
      const match = active?.sources.find((s) => cite.startsWith(s.title));
      setHighlightedSourceId(match?.id ?? null);
    },
    [active],
  );

  const handleSourceSelect = useCallback((source: Source) => {
    setHighlightedSourceId((prev) => (prev === source.id ? null : source.id));
  }, []);

  if (!active) return null;

  return (
    <div
      className={`app ${full ? "full" : ""} ${sidebarOpen ? "sidebar-open" : "sidebar-closed"} ${
        railOpen ? "rail-open" : "rail-closed"
      }`.trim()}
    >
      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <ChatSidebar
        conversations={conversations}
        activeId={active.id}
        pinnedIds={pinnedIds}
        onClose={() => setSidebarOpen(false)}
        onSelect={(id) => {
          setActiveId(id);
          if (window.innerWidth <= 640) setSidebarOpen(false);
        }}
        onNewChat={handleNewChat}
        onRename={(id, title) => void handleRename(id, title)}
        onTogglePin={(id) =>
          setPinnedIds((prev) => {
            const next = prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id];
            writePinned(account?.userId, next);
            return next;
          })
        }
        onDelete={handleDelete}
        onExport={handleExport}
        onShare={handleShare}
      />

      <main className="chat">
        <div className="chat-head">
          <div className="chat-head-title">
            <h4>{active.title}</h4>
            <div className="sub">{toast ?? (loading ? "Loading conversations…" : active.subtitle)}</div>
          </div>
          <div className="badges">
            <span className="badge live">
              <span className="dot" aria-hidden="true" /> LIVE
            </span>
            <span className="badge">RAG · {active.sources.length} sources</span>
            <button
              type="button"
              className={`rail-toggle ${railOpen ? "on" : ""}`.trim()}
              onClick={() => setRailOpen((open) => !open)}
              aria-label={railOpen ? "Hide sources panel" : "Show sources panel"}
              aria-expanded={railOpen}
              title={railOpen ? "Hide sources" : "Show sources"}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="14" y="4" width="7" height="16" rx="1.5" stroke="currentColor" strokeWidth="1.7" />
                <path d="M4 7h8M4 12h8M4 17h8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        <SpeechControls isSpeaking={isSpeaking} onStopSpeaking={stop} />

        <MessageList
          messages={active.messages}
          speakingId={speakingId}
          onSpeak={handleSpeak}
          onCiteClick={handleCiteClick}
        />

        <Composer
          onSend={handleSend}
          onAttach={handleAttach}
          attachName={attachName}
          attachState={attachState}
          disabled={thinking || loading || attachState === "uploading"}
        />
      </main>

      <SourcesRail
        sources={active.sources}
        files={chatFiles}
        highlightedId={highlightedSourceId}
        onSelect={handleSourceSelect}
        onDeleteFile={(filename) => void handleDeleteFile(filename)}
      />
      <button
        type="button"
        className="rail-backdrop"
        aria-label="Close sources panel"
        onClick={() => setRailOpen(false)}
      />
    </div>
  );
}
