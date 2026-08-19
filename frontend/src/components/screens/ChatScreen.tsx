"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import ChatSidebar from "@/components/chat/ChatSidebar";
import Composer from "@/components/chat/Composer";
import MessageList from "@/components/chat/MessageList";
import SourcesRail from "@/components/chat/SourcesRail";
import SpeechControls from "@/components/chat/SpeechControls";
import { CONVERSATIONS, draftAnswer, type Conversation, type Message, type Source } from "@/lib/data";
import { useSidebar, SidebarToggle } from "@/lib/sidebar-context";
import { useSpeechSettings } from "@/lib/speech/useSpeechSettings";
import { useSpeaker } from "@/lib/useSpeech";

const REPLY_DELAY_MS = 1300;

let idCounter = 0;
function nextId(prefix: string) {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}

export default function ChatScreen({ full = true }: { full?: boolean }) {
  const [conversations, setConversations] = useState<Conversation[]>(CONVERSATIONS);
  const [activeId, setActiveId] = useState(CONVERSATIONS[0].id);
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);
  const [thinking, setThinking] = useState(false);
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

  const updateConversation = useCallback(
    (id: string, update: (conversation: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((c) => (c.id === id ? update(c) : c)));
    },
    [],
  );

  const handleSend = useCallback(
    (text: string) => {
      if (!active) return;

      const userMessage: Message = { id: nextId("u"), role: "user", text };
      const pendingId = nextId("b");

      updateConversation(active.id, (c) => ({
        ...c,
        messages: [...c.messages, userMessage, { id: pendingId, role: "bot", text: "", pending: true }],
      }));
      setThinking(true);

      window.setTimeout(() => {
        let answerText = "";
        updateConversation(active.id, (c) => {
          const answer = draftAnswer(text, c);
          answerText = answer.text;
          return {
            ...c,
            subtitle:
              c.sources.length > 0
                ? `Grounded on ${c.sources.length} documents · updated just now`
                : "No documents retrieved yet",
            messages: c.messages.map((m) =>
              m.id === pendingId
                ? { id: pendingId, role: "bot", text: answer.text, cite: answer.cite }
                : m,
            ),
          };
        });
        speakIfAutoRead(pendingId, answerText);
        setThinking(false);
      }, REPLY_DELAY_MS);
    },
    [active, updateConversation, speakIfAutoRead],
  );

  const handleNewChat = useCallback(() => {
    const conversation: Conversation = {
      id: nextId("chat"),
      title: "New chat",
      group: "Today",
      subtitle: "No documents retrieved yet",
      messages: [],
      sources: [],
    };
    setConversations((prev) => [conversation, ...prev]);
    setActiveId(conversation.id);
  }, []);

  const handleDelete = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (next.length === 0) return prev;
        if (id === activeId) setActiveId(next[0].id);
        return next;
      });
      setPinnedIds((prev) => prev.filter((p) => p !== id));
      flash("Conversation deleted");
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
            <div className="sub">{toast ?? active.subtitle}</div>
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

        <Composer onSend={handleSend} disabled={thinking} />
      </main>

      <SourcesRail
        sources={active.sources}
        highlightedId={highlightedSourceId}
        onSelect={handleSourceSelect}
      />
    </div>
  );
}
