"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import FaceCamera from "@/components/FaceCamera";

const SCAN_MS = 2800;
const TICK_MS = 40;

type Props = {
  onSuccess: () => void;
  onCancel: () => void;
};

export default function FaceVerifyScreen({ onSuccess, onCancel }: Props) {
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<"scanning" | "matched">("scanning");
  const timerRef = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const increment = 100 / (SCAN_MS / TICK_MS);
    timerRef.current = window.setInterval(() => {
      setProgress((prev) => {
        const next = prev + increment;
        if (next >= 100) {
          clearTimer();
          setPhase("matched");
          return 100;
        }
        return next;
      });
    }, TICK_MS);

    return clearTimer;
  }, [clearTimer]);

  useEffect(() => {
    if (phase !== "matched") return;
    const t = window.setTimeout(onSuccess, 1200);
    return () => window.clearTimeout(t);
  }, [phase, onSuccess]);

  const complete = progress >= 100;

  return (
    <div className="face-full face-verify">
      <div className="face-copy">
        <div className="face-step">{phase === "matched" ? "Verified" : "Face ID"}</div>

        {phase === "matched" ? (
          <>
            <h3>
              Welcome
              <br />
              <b>back.</b>
            </h3>
            <p>Face matched. Opening your workspace…</p>
          </>
        ) : (
          <>
            <h3>
              Look at the
              <br />
              <b>camera.</b>
            </h3>
            <p>Hold still while we verify your face. Well-lit, face inside the frame.</p>
          </>
        )}

        <div className="face-actions">
          {phase === "scanning" && (
            <>
              <button type="button" className="btn on-dark" disabled={!complete}>
                {complete ? "Verified" : "Scanning…"}
              </button>
              <button type="button" className="btn on-dark-ghost" onClick={onCancel}>
                Use password instead
              </button>
            </>
          )}
        </div>
      </div>

      <div className="face-visual">
        <div className={`face-circle ${phase === "matched" ? "matched" : ""}`.trim()}>
          <FaceCamera active={phase === "scanning"} />
          <div className="face-scan" aria-hidden="true" />
          <div className="face-outline" aria-hidden="true" />
          <div className="face-corners" aria-hidden="true" />
          <div
            className="face-percent"
            role="progressbar"
            aria-valuenow={Math.round(progress)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            {phase === "matched" ? (
              <>
                <b>✓</b>
                <span className="lbl">Matched</span>
              </>
            ) : (
              <>
                <b>{Math.round(progress)}</b>%
                <span className="lbl">{complete ? "Processing" : "Scanning"}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
