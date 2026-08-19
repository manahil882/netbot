"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import FaceCamera from "@/components/FaceCamera";
import { ENROLL_STEPS } from "@/lib/data";
import { useAuth } from "@/lib/auth-context";

const CAPTURE_MS = 3500;
const TICK_MS = 40;

type Props = {
  onComplete?: () => void;
  autoStart?: boolean;
};

export default function EnrollScreen({ onComplete, autoStart = true }: Props) {
  const router = useRouter();
  const { login } = useAuth();
  const [stepIndex, setStepIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [capturing, setCapturing] = useState(autoStart);
  const [done, setDone] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const timerRef = useRef<number | null>(null);
  const finishTimerRef = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const clearFinishTimer = useCallback(() => {
    if (finishTimerRef.current !== null) {
      window.clearTimeout(finishTimerRef.current);
      finishTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!capturing || done || finishing) return;

    const increment = 100 / (CAPTURE_MS / TICK_MS);
    timerRef.current = window.setInterval(() => {
      setProgress((prev) => {
        const next = prev + increment;
        if (next >= 100) {
          clearTimer();
          setCapturing(false);
          return 100;
        }
        return next;
      });
    }, TICK_MS);

    return clearTimer;
  }, [capturing, stepIndex, done, finishing, clearTimer]);

  useEffect(() => () => clearFinishTimer(), [clearFinishTimer]);

  const step = ENROLL_STEPS[stepIndex];
  const isLast = stepIndex === ENROLL_STEPS.length - 1;
  const captureComplete = progress >= 100;

  function goToStep(index: number) {
    clearTimer();
    clearFinishTimer();
    setFinishing(false);
    setStepIndex(index);
    setProgress(0);
    setCapturing(true);
    setDone(false);
  }

  function finish() {
    login();
    if (onComplete) {
      onComplete();
      return;
    }
    router.replace("/chat");
  }

  function beginFinish() {
    setDone(true);
    setCapturing(false);
    setFinishing(true);
    clearTimer();

    finishTimerRef.current = window.setTimeout(() => {
      finish();
    }, 1400);
  }

  function handleNext() {
    if (!captureComplete) return;

    if (isLast) {
      beginFinish();
      return;
    }

    goToStep(stepIndex + 1);
  }

  return (
    <div className="face-full">
      <div className="face-copy">
        <div className="face-step">
          {done ? "All set" : `Step ${stepIndex + 1} of ${ENROLL_STEPS.length}`}
        </div>

        {done ? (
          <>
            <h3>
              Face ID is
              <br />
              <b>ready to go.</b>
            </h3>
            <p>Enrollment complete. Taking you to netbot…</p>
          </>
        ) : (
          <>
            <h3>
              {step.heading[0]}
              <br />
              <b>{step.heading[1]}</b>
            </h3>
            <p>{step.copy}</p>
          </>
        )}

        <div className="steps">
          {ENROLL_STEPS.map((s, i) => {
            const state = done || i < stepIndex ? "done" : i === stepIndex ? "on" : "";
            return (
              <button
                key={s.id}
                type="button"
                className={`stepdot ${state}`.trim()}
                onClick={() => goToStep(i)}
                aria-label={`Recapture ${s.label}`}
                disabled={finishing}
              >
                <span className="b" aria-hidden="true" />
                <small>{s.label}</small>
              </button>
            );
          })}
        </div>

        <div className="face-actions">
          {done ? (
            <button type="button" className="btn on-dark" disabled>
              Opening netbot…
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn on-dark"
                onClick={handleNext}
                disabled={!captureComplete}
              >
                {captureComplete ? (isLast ? "Finish enrollment" : "Next capture") : "Capturing…"}
              </button>
              <button
                type="button"
                className="btn on-dark-ghost"
                onClick={() => goToStep(stepIndex)}
                disabled={!captureComplete}
              >
                Retake
              </button>
            </>
          )}
        </div>
      </div>

      <div className="face-visual">
        <div className={`face-circle ${done ? "matched" : ""}`.trim()}>
          <FaceCamera active={!done} />
          <div className="face-scan" aria-hidden="true" />
          <div className="face-outline" aria-hidden="true" />
          <div className="face-corners" aria-hidden="true" />
          <div
            className="face-percent"
            role="progressbar"
            aria-valuenow={Math.round(done ? 100 : progress)}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            {done ? (
              <>
                <b>✓</b>
                <span className="lbl">Enrolled</span>
              </>
            ) : (
              <>
                <b>{Math.round(progress)}</b>%
                <span className="lbl">{captureComplete ? "Captured" : "Capturing"}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
