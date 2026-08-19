"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/lib/data";
import { USER } from "@/lib/data";

type Props = {
  messages: Message[];
  speakingId: string | null;
  onSpeak: (message: Message) => void;
  onCiteClick: (cite: string) => void;
};

export default function MessageList({ messages, speakingId, onSpeak, onCiteClick }: Props) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="messages">
      {messages.map((message) => (
        <div key={message.id} className={`msg ${message.role}`}>
          <div className="av" aria-hidden="true">
            {message.role === "user" ? USER.initial : "N"}
          </div>

          <div className="bubble">
            {message.pending ? (
              <span className="typing" role="status" aria-label="netbot is typing">
                <i />
                <i />
                <i />
              </span>
            ) : (
              <>
                {message.text}
                {message.role === "bot" && (
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
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
