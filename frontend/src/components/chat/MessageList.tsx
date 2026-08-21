"use client";

import { useEffect, useRef, useState } from "react";
import type { Message } from "@/lib/data";
import { accountInitials } from "@/lib/auth";
import { useAuth } from "@/lib/auth-context";
import MarkdownBody from "@/components/chat/MarkdownBody";
import NetsolLogo from "@/components/NetsolLogo";
import { stripMarkdown } from "@/lib/markdown";

type Props = {
  messages: Message[];
  speakingId: string | null;
  onSpeak: (message: Message) => void;
  onCiteClick: (cite: string) => void;
};

export default function MessageList({ messages, speakingId, onSpeak, onCiteClick }: Props) {
  const { account } = useAuth();
  const endRef = useRef<HTMLDivElement | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function copyText(message: Message) {
    const text = message.role === "bot" ? stripMarkdown(message.text) : message.text;
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(message.id);
      window.setTimeout(() => setCopiedId((id) => (id === message.id ? null : id)), 1600);
    } catch {
      // Ignore clipboard failures.
    }
  }

  return (
    <div className="messages">
      {messages.map((message) => (
        <div key={message.id} className={`msg ${message.role}`}>
          <div className="av" aria-hidden="true">
            {message.role === "user" ? accountInitials(account) : <NetsolLogo size={34} />}
          </div>

          <div className="msg-stack">
            <div className="bubble">
              {message.pending ? (
                <span className="typing" role="status" aria-label="NetBot is typing">
                  <i />
                  <i />
                  <i />
                </span>
              ) : message.role === "bot" ? (
                <MarkdownBody text={message.text} />
              ) : (
                message.text
              )}
            </div>

            {!message.pending && message.role === "bot" && (
              <div className="bubble-actions">
                {message.cite && (
                  <button
                    type="button"
                    className="cite"
                    onClick={() => onCiteClick(message.cite as string)}
                  >
                    📄 {message.cite}
                  </button>
                )}
                <button
                  type="button"
                  className={`speak-btn ${speakingId === message.id ? "on" : ""}`.trim()}
                  onClick={() => onSpeak(message)}
                >
                  🔊 {speakingId === message.id ? "Stop" : "Play"}
                </button>
                <button
                  type="button"
                  className="copy-btn"
                  onClick={() => void copyText(message)}
                  aria-label="Copy message"
                >
                  {copiedId === message.id ? "Copied" : "Copy"}
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
