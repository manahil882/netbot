"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ChatSidebar from "@/components/chat/ChatSidebar";
import Composer from "@/components/chat/Composer";
import MessageList from "@/components/chat/MessageList";
import SourcesRail from "@/components/chat/SourcesRail";
import SpeechControls from "@/components/chat/SpeechControls";
import {
  getThreadMessages,
  listThreads,
  sendChat,
  type Citation,
} from "@/lib/api/chat";
import { ApiError } from "@/lib/api/config";
import { type Conversation, type Message, type Source } from "@/lib/data";
import { useSidebar, SidebarToggle } from "@/lib/sidebar-context";
import { useSpeechSettings } from "@/lib/speech/useSpeechSettings";
import { useSpeaker } from "@/lib/useSpeech";

const NEW_CHAT_ID = "new-chat";

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

export default function ChatScreen({ full = true }: { full?: boolean }) {
  const [conversations, setConversations] = useState<Conversation[]>([emptyConversation()]);
  const [activeId, setActiveId] = useState(NEW_CHAT_ID);
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);
  const [thinking, setThinking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [highlightedSourceId, setHighlightedSourceId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
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
        setConversations(loaded.length > 0 ? loaded : [emptyConversation()]);
        setActiveId(loaded[0]?.id ?? NEW_CHAT_ID);
      } catch (err) {
        flash(err instanceof ApiError ? err.message : "Could not load conversations");
        setConversations([emptyConversation()]);
      } finally {
        setLoading(false);
      }
    }

    void loadThreads();
  }, [flash]);

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
        flash(err instanceof ApiError ? err.message : "Could not send message");
      } finally {
        setThinking(false);
      }
    },
    [active, updateConversation, speakIfAutoRead, flash],
  );

  const handleNewChat = useCallback(() => {
    const exists = conversations.some((c) => c.id === NEW_CHAT_ID);
    if (!exists) {
      setConversations((prev) => [emptyConversation(), ...prev]);
    }
    setActiveId(NEW_CHAT_ID);
  }, [conversations]);

  const handleDelete = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (next.length === 0) return [emptyConversation()];
        if (id === activeId) setActiveId(next[0].id);
        return next;
      });
      setPinnedIds((prev) => prev.filter((p) => p !== id));
      flash("Conversation removed locally");
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
    <div className={`app ${full ? "full" : ""} ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`.trim()}>
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
        onRename={(id, title) => updateConversation(id, (c) => ({ ...c, title }))}
        onTogglePin={(id) =>
          setPinnedIds((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]))
        }
        onDelete={handleDelete}
        onExport={handleExport}
        onShare={handleShare}
      />

      <main className="chat">
        <div className="chat-head">
          <SidebarToggle />

          <div className="chat-head-title">
            <h4>{active.title}</h4>
            <div className="sub">{toast ?? (loading ? "Loading conversations…" : active.subtitle)}</div>
          </div>
          <div className="badges">
            <span className="badge live">
              <span className="dot" aria-hidden="true" /> LIVE
            </span>
            <span className="badge">RAG · {active.sources.length} sources</span>
          </div>
        </div>

        <SpeechControls isSpeaking={isSpeaking} onStopSpeaking={stop} />

        <MessageList
          messages={active.messages}
          speakingId={speakingId}
          onSpeak={handleSpeak}
          onCiteClick={handleCiteClick}
        />

        <Composer onSend={handleSend} disabled={thinking || loading} />
      </main>

      <SourcesRail
        sources={active.sources}
        highlightedId={highlightedSourceId}
        onSelect={handleSourceSelect}
      />
    </div>
  );
}
