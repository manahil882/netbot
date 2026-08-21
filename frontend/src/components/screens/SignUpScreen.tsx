"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PasswordField from "@/components/PasswordField";
import EnrollScreen from "@/components/screens/EnrollScreen";
import {
  apiCheckEmailAvailable,
  apiRegister,
  apiSendVerificationCode,
  apiVerifyEmailCode,
} from "@/lib/api/client";
import { ApiError } from "@/lib/api/config";
import { isStrongPassword } from "@/lib/auth";
import { useAuth } from "@/lib/auth-context";
import NetsolLogo from "@/components/NetsolLogo";

type Phase = "account" | "verify" | "face";

type PendingSignup = {
  name: string;
  email: string;
  password: string;
  emailToken: string;
};

export default function SignUpScreen() {
  const router = useRouter();
  const { setSession } = useAuth();
  const [phase, setPhase] = useState<Phase>("account");
  const [pending, setPending] = useState<PendingSignup | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [code, setCode] = useState("");
  const [devCodeHint, setDevCodeHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleAccountSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (name.trim().length < 2) {
      setError("Enter your full name.");
      return;
    }
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError("Enter a valid email address.");
      return;
    }
    if (!isStrongPassword(password)) {
      setError("Use a stronger password — at least 8 characters with upper, lower, and a number.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setError(null);
    setBusy(true);
    try {
      const available = await apiCheckEmailAvailable(normalizedEmail);
      if (!available) {
        setError("An account already exists for this email. Please sign in instead.");
        return;
      }
      const sent = await apiSendVerificationCode(normalizedEmail);
      setDevCodeHint(sent.dev_code ?? null);
      setPending({
        name: name.trim(),
        email: normalizedEmail,
        password,
        emailToken: "",
      });
      setCode("");
      setPhase("verify");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start verification. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleVerifySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!pending) return;
    const trimmed = code.trim();
    if (!/^\d{6}$/.test(trimmed)) {
      setError("Enter the 6-digit code from your email.");
      return;
    }

    setError(null);
    setBusy(true);
    try {
      const verified = await apiVerifyEmailCode(pending.email, trimmed);
      setPending({ ...pending, emailToken: verified.email_token });
      setDevCodeHint(null);
      setPhase("face");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invalid or expired code.");
    } finally {
      setBusy(false);
    }
  }

  async function resendCode() {
    if (!pending) return;
    setError(null);
    setBusy(true);
    try {
      const sent = await apiSendVerificationCode(pending.email);
      setDevCodeHint(sent.dev_code ?? null);
      setCode("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend code.");
    } finally {
      setBusy(false);
    }
  }

  if (phase === "face" && pending?.emailToken) {
    return (
      <EnrollScreen
        autoStart
        allowSkip
        onComplete={async (faceImage) => {
          const register = async (image: Blob | null) => {
            const session = await apiRegister(
              pending.name,
              pending.email,
              pending.password,
              pending.emailToken,
              image,
            );
            setSession(
              session.access_token,
              {
                name: session.name,
                email: session.email,
                userId: session.user_id,
              },
              Boolean(session.face_enrolled ?? image),
            );
            router.replace("/chat");
          };

          try {
            await register(faceImage);
          } catch (err) {
            const message = err instanceof ApiError ? err.message : "Registration failed";
            const faceUnavailable =
              faceImage !== null &&
              (message.toLowerCase().includes("face") ||
                message.toLowerCase().includes("ml deps") ||
                (err instanceof ApiError && err.status === 503));

            if (faceUnavailable) {
              await register(null);
              return;
            }
            throw new Error(message);
          }
        }}
      />
    );
  }

  if (phase === "verify" && pending) {
    return (
      <div className="login-split">
        <div className="login-brand">
          <div className="lb-brand">
            <NetsolLogo size={36} /> netbot
          </div>
          <h2 className="lb-title">
            Check
            <br />
            <span className="amp">your</span> <b>inbox.</b>
          </h2>
          <div className="lb-foot">
            <span>v2.0</span>
            <span>Enterprise</span>
            <span>SOC 2</span>
          </div>
          <div className="lb-orbits" aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
        </div>

        <form className="login-form" onSubmit={handleVerifySubmit} noValidate>
          <h3 className="lf-title">
            Enter <b>verification code.</b>
          </h3>
          <p className="lf-sub">
            We sent a 6-digit code to <b>{pending.email}</b>.
          </p>

          <div className="field">
            <label htmlFor="signup-code">Verification code</label>
            <input
              id="signup-code"
              className="inp"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="123456"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            />
          </div>

          {devCodeHint && (
            <p className="lf-sub">
              Dev mode code: <b>{devCodeHint}</b>
            </p>
          )}

          {error && <div className="field-error">{error}</div>}

          <button type="submit" className="btn primary block" disabled={busy}>
            {busy ? "Verifying…" : "Verify email →"}
          </button>

          <button
            type="button"
            className="btn ghost block"
            disabled={busy}
            onClick={() => void resendCode()}
            style={{ marginTop: 10 }}
          >
            Resend code
          </button>

          <div className="foot">
            <button
              type="button"
              onClick={() => {
                setPhase("account");
                setError(null);
                setDevCodeHint(null);
              }}
            >
              ← Back
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="login-split">
      <div className="login-brand">
        <div className="lb-brand">
          <NetsolLogo size={36} /> netbot
        </div>
        <h2 className="lb-title">
          Join
          <br />
          <span className="amp">on</span> <b>
            speaking
            <br />
            terms.
          </b>
        </h2>
        <div className="lb-foot">
          <span>v2.0</span>
          <span>Enterprise</span>
          <span>SOC 2</span>
        </div>
        <div className="lb-orbits" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
      </div>

      <form className="login-form" onSubmit={handleAccountSubmit} noValidate>
        <h3 className="lf-title">
          Create your <b>account.</b>
        </h3>
        <p className="lf-sub">We’ll email you a verification code next.</p>

        <div className="field">
          <label htmlFor="signup-name">Full name</label>
          <input
            id="signup-name"
            className="inp"
            autoComplete="name"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="signup-email">Work email</label>
          <input
            id="signup-email"
            className="inp"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <PasswordField
          id="signup-password"
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          showStrength
        />

        <PasswordField
          id="signup-confirm"
          label="Confirm password"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
        />

        {error && <div className="field-error">{error}</div>}

        <button type="submit" className="btn primary block" disabled={busy}>
          {busy ? "Sending code…" : "Continue →"}
        </button>

        <div className="foot">
          Already have an account? <Link href="/signin">Sign in</Link>
        </div>
      </form>
    </div>
  );
}
