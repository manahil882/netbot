"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PasswordField from "@/components/PasswordField";
import FaceVerifyScreen from "@/components/screens/FaceVerifyScreen";
import { apiLogin } from "@/lib/api/client";
import { ApiError } from "@/lib/api/config";
import { useAuth } from "@/lib/auth-context";
import NetsolLogo from "@/components/NetsolLogo";

export default function SignInScreen() {
  const router = useRouter();
  const { authed, setSession } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [faceVerify, setFaceVerify] = useState(false);

  function goToChat() {
    router.replace("/chat");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError("Enter a valid work email address.");
      return;
    }
    if (!password) {
      setError("Enter your password.");
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      const session = await apiLogin(normalizedEmail, password);
      setSession(session.access_token, {
        name: session.name,
        email: session.email,
        userId: session.user_id,
      });
      goToChat();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign in failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleFaceUnlock() {
    setError(null);
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError("Enter your email first, then use Face ID.");
      return;
    }
    setFaceVerify(true);
  }

  if (faceVerify) {
    return (
      <FaceVerifyScreen
        email={email.trim().toLowerCase()}
        onSuccess={goToChat}
        onCancel={() => setFaceVerify(false)}
      />
    );
  }

  return (
    <div className="login-split">
      <div className="login-brand">
        <div className="lb-brand">
          <NetsolLogo size={36} /> netbot
        </div>
        <h2 className="lb-title">
          Knowledge
          <br />
          <span className="amp">on</span> <b>speaking
          <br />
          terms.</b>
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

      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <h3 className="lf-title">
          Welcome <b>back.</b>
        </h3>
        <p className="lf-sub">Sign in with the account you created during signup.</p>

        <div className="field">
          <label htmlFor="signin-email">Email</label>
          <input
            id="signin-email"
            className="inp"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <PasswordField
          id="signin-password"
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
        />

        {error && <div className="field-error">{error}</div>}

        <button type="submit" className="btn primary block" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <div className="or">OR</div>

        <button
          type="button"
          className="btn face block"
          onClick={handleFaceUnlock}
          disabled={submitting}
        >
          <span className="pulse" aria-hidden="true" />
          Continue with Face ID
        </button>

        <div className="foot">
          New here? <Link href="/signup">Create an account</Link>
        </div>

        {authed && (
          <button type="button" className="btn ghost block" onClick={() => router.replace("/chat")}>
            Already signed in — continue to chat →
          </button>
        )}
      </form>
    </div>
  );
}
