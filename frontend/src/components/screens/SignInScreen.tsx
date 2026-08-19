"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PasswordField from "@/components/PasswordField";
import FaceVerifyScreen from "@/components/screens/FaceVerifyScreen";
import { useAuth } from "@/lib/auth-context";

export default function SignInScreen() {
  const router = useRouter();
  const { authed, account, faceEnrolled, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [faceVerify, setFaceVerify] = useState(false);

  function goToChat() {
    login();
    router.replace("/chat");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!account) {
      setError("No account yet. Create one first — Face ID is set up during signup.");
      return;
    }

    const normalizedEmail = email.trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setError("Enter a valid work email address.");
      return;
    }
    if (normalizedEmail !== account.email) {
      setError("No account found for this email. Check the address or create an account.");
      return;
    }
    if (password !== account.password) {
      setError("Incorrect password.");
      return;
    }

    setError(null);
    setSubmitting(true);
    goToChat();
  }

  function handleFaceUnlock() {
    setError(null);

    if (!account) {
      setError("Create an account first. Face ID is enrolled during signup.");
      return;
    }
    if (!faceEnrolled) {
      setError("Face ID is not set up yet. Finish signup to enroll your face.");
      return;
    }

    setFaceVerify(true);
  }

  if (faceVerify) {
    return (
      <FaceVerifyScreen
        onSuccess={goToChat}
        onCancel={() => setFaceVerify(false)}
      />
    );
  }

  return (
    <div className="login-split">
      <div className="login-brand">
        <div className="lb-brand">
          <span className="m">N</span> netbot
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
        <p className="lf-sub">
          {account
            ? `Sign in as ${account.name.split(" ")[0]}.`
            : "Sign in with the account you created during signup."}
        </p>

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

        {!account && (
          <div className="field-note">
            New to netbot?{" "}
            <Link href="/signup">Create an account</Link> — you&apos;ll set up Face ID in step 2.
          </div>
        )}

        <button type="submit" className="btn primary block" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <div className="or">OR</div>

        <button
          type="button"
          className="btn face block"
          onClick={handleFaceUnlock}
          disabled={submitting || !account || !faceEnrolled}
          title={
            !account
              ? "Create an account first"
              : !faceEnrolled
                ? "Complete signup to enroll Face ID"
                : "Sign in with Face ID"
          }
        >
          <span className="pulse" aria-hidden="true" />
          Continue with Face ID
        </button>

        {account && !faceEnrolled && (
          <div className="field-note">
            Face ID not enrolled yet.{" "}
            <Link href="/signup">Finish signup</Link> to capture your face.
          </div>
        )}

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
