"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import PasswordField from "@/components/PasswordField";
import EnrollScreen from "@/components/screens/EnrollScreen";
import { apiRegister } from "@/lib/api/client";
import { ApiError } from "@/lib/api/config";
import { isStrongPassword } from "@/lib/auth";
import { useAuth } from "@/lib/auth-context";

type Phase = "account" | "face";

type PendingSignup = {
  name: string;
  email: string;
  password: string;
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
  const [error, setError] = useState<string | null>(null);

  function handleAccountSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (name.trim().length < 2) {
      setError("Enter your full name.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
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

    setPending({
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password,
    });
    setError(null);
    setPhase("face");
  }

  if (phase === "face" && pending) {
    return (
      <EnrollScreen
        autoStart
        onComplete={async (faceImage) => {
          try {
            const session = await apiRegister(
              pending.name,
              pending.email,
              pending.password,
              faceImage,
            );
            setSession(
              session.access_token,
              {
                name: session.name,
                email: session.email,
                userId: session.user_id,
              },
              true,
            );
            router.replace("/chat");
          } catch (err) {
            throw new Error(err instanceof ApiError ? err.message : "Registration failed");
          }
        }}
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
          Join
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

      <form className="login-form" onSubmit={handleAccountSubmit} noValidate>
        <h3 className="lf-title">
          Create your <b>account.</b>
        </h3>
        <p className="lf-sub">Step 1 of 2 — then enroll Face ID.</p>

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

        <button type="submit" className="btn primary block">
          Continue to Face ID →
        </button>

        <div className="foot">
          Already have an account? <Link href="/signin">Sign in</Link>
        </div>
      </form>
    </div>
  );
}
