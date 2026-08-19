"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useDictation } from "@/lib/useSpeech";

type Props = {
  onSend: (text: string) => void;
  disabled?: boolean;
};

export default function Composer({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState("");
  const [attachment, setAttachment] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const appendTranscript = useCallback((transcript: string) => {
    setValue((prev) => (prev ? `${prev} ${transcript}` : transcript));
  }, []);

  const { listening, toggle: toggleMic } = useDictation(appendTranscript);

  // Grow the textarea with its content up to the CSS max-height.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(attachment ? `${trimmed}\n\n(attached: ${attachment})` : trimmed);
    setValue("");
    setAttachment(null);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <div className="composer-row">
      <div className={`composer ${listening ? "active" : ""}`.trim()}>
        <textarea
          ref={textareaRef}
          className="txt"
          rows={1}
          placeholder={listening ? "Listening…" : "Ask netbot anything…"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Message netbot"
        />

        {listening && (
          <span className="waveform" title="listening" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </span>
        )}

        <input
          ref={fileRef}
          type="file"
          hidden
          onChange={(e) => setAttachment(e.target.files?.[0]?.name ?? null)}
        />

        <button
          type="button"
          className="icobtn"
          title={attachment ?? "Attach a document"}
          aria-label="Attach a document"
          onClick={() => fileRef.current?.click()}
        >
          ＋
        </button>

        <button
          type="button"
          className={`icobtn mic ${listening ? "recording" : ""}`.trim()}
          title={listening ? "Stop listening" : "Dictate your question"}
          aria-label={listening ? "Stop listening" : "Dictate your question"}
          aria-pressed={listening}
          onClick={toggleMic}
        >
          🎙
        </button>

        <button
          type="button"
          className="icobtn send"
          title="Send"
          aria-label="Send message"
          onClick={submit}
          disabled={disabled || !value.trim()}
        >
          ↑
        </button>
      </div>
    </div>
  );
}
