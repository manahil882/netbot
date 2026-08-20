"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import FaceCamera, { type FaceCameraHandle } from "@/components/FaceCamera";
import { apiFaceLogin } from "@/lib/api/client";
import { captureVideoFrame } from "@/lib/face-capture";
import { useAuth } from "@/lib/auth-context";

const SCAN_MS = 2800;
const TICK_MS = 40;

type Props = {
  email: string;
  onSuccess: () => void | Promise<void>;
  onCancel: () => void;
};

export default function FaceVerifyScreen({ email, onSuccess, onCancel }: Props) {
  const { setSession } = useAuth();
  const cameraRef = useRef<FaceCameraHandle | null>(null);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<"scanning" | "matched" | "error">("scanning");
  const [error, setError] = useState<string | null>(null);
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
          return 100;
        }
        return next;
      });
    }, TICK_MS);

    return clearTimer;
  }, [clearTimer]);

  useEffect(() => {
    if (progress < 100 || phase !== "scanning") return;

    async function verify() {
      try {
        const video = cameraRef.current?.getVideoElement();
        const faceImage = video ? await captureVideoFrame(video) : null;
        if (!faceImage) {
          throw new Error("Could not capture your face. Try again.");
        }

        const session = await apiFaceLogin(email, faceImage);
        setSession(
          session.access_token,
          {
            name: session.name,
            email: session.email,
            userId: session.user_id,
          },
          true,
        );
        setPhase("matched");
        window.setTimeout(() => void onSuccess(), 1200);
      } catch (err) {
        setPhase("error");
        setError(err instanceof Error ? err.message : "Face verification failed");
      }
    }

    void verify();
  }, [progress, phase, email, onSuccess, setSession]);

  const complete = progress >= 100;

  return (
    <div className="face-full face-verify">
      <div className="face-copy">
        <div className="face-step">
          {phase === "matched" ? "Verified" : phase === "error" ? "Try again" : "Face ID"}
        </div>

        {phase === "matched" ? (
          <>
            <h3>
              Welcome
              <br />
              <b>back.</b>
            </h3>
            <p>Face matched. Opening your workspace…</p>
          </>
        ) : phase === "error" ? (
          <>
            <h3>
              Face not
              <br />
              <b>recognized.</b>
            </h3>
            <p>{error}</p>
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
                {complete ? "Verifying…" : "Scanning…"}
              </button>
              <button type="button" className="btn on-dark-ghost" onClick={onCancel}>
                Use password instead
              </button>
            </>
          )}
          {phase === "error" && (
            <button type="button" className="btn on-dark-ghost" onClick={onCancel}>
              Use password instead
            </button>
          )}
        </div>
      </div>

      <div className="face-visual">
        <div className={`face-circle ${phase === "matched" ? "matched" : ""}`.trim()}>
          <FaceCamera ref={cameraRef} active={phase === "scanning"} />
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
