"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiDeleteAccount, apiUpdateProfile } from "@/lib/api/client";
import { ApiError } from "@/lib/api/config";
import { AVATAR_OPTIONS } from "@/lib/data";
import { useAuth } from "@/lib/auth-context";

type EditableField = "name" | null;

const AVATAR_KEY = "netbot.avatarId";

export default function ProfileScreen() {
  const router = useRouter();
  const { account, faceEnrolled, logout, deleteAccount, updateAccount } = useAuth();
  const [avatarId, setAvatarId] = useState(AVATAR_OPTIONS[0].id);
  const [editing, setEditing] = useState<EditableField>(null);
  const [draft, setDraft] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = window.sessionStorage.getItem(AVATAR_KEY);
      if (saved && AVATAR_OPTIONS.some((a) => a.id === saved)) setAvatarId(saved);
    } catch {
      // ignore
    }
  }, []);

  function pickAvatar(id: string) {
    setAvatarId(id);
    try {
      window.sessionStorage.setItem(AVATAR_KEY, id);
    } catch {
      // ignore
    }
  }

  const name = account?.name ?? "";
  const email = account?.email ?? "";
  const avatar = AVATAR_OPTIONS.find((a) => a.id === avatarId) ?? AVATAR_OPTIONS[0];

  function beginEditName() {
    setEditing("name");
    setDraft(name);
    setError(null);
  }

  async function commitEdit() {
    const value = draft.trim();
    if (!value || editing !== "name") {
      setEditing(null);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await apiUpdateProfile(value);
      updateAccount({ name: updated.name });
      setEditing(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update name");
    } finally {
      setBusy(false);
    }
  }

  async function confirmDelete() {
    setBusy(true);
    setError(null);
    try {
      await apiDeleteAccount();
      deleteAccount();
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete account");
      setBusy(false);
    }
  }

  return (
    <div className="profile-shell">
      <div className="profile-card">
        <div className="pc-head">
          <div
            className="pc-avatar"
            style={{ background: avatar.background, color: avatar.color }}
          >
            {avatar.glyph}
            <button
              type="button"
              className="cam"
              aria-label="Change avatar"
              onClick={() => {
                const index = AVATAR_OPTIONS.findIndex((a) => a.id === avatarId);
                pickAvatar(AVATAR_OPTIONS[(index + 1) % AVATAR_OPTIONS.length].id);
              }}
            >
              ✎
            </button>
          </div>

          <div className="pc-who">
            <b>{name || "Your account"}</b>
            <span>{email || "No email on this session"}</span>
            <div className={`pc-badge ${faceEnrolled ? "" : "off"}`.trim()}>
              <span className="d" aria-hidden="true" />
              {faceEnrolled ? "Face ID enrolled" : "Face ID not set up"}
            </div>
          </div>
        </div>

        <div className="pc-avatars">
          <span className="label">Avatar</span>
          {AVATAR_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              className={`avn ${option.id === avatarId ? "on" : ""}`.trim()}
              style={{ background: option.background, color: option.color }}
              onClick={() => pickAvatar(option.id)}
              aria-label={`Use avatar ${option.glyph}`}
              aria-pressed={option.id === avatarId}
            >
              {option.glyph}
            </button>
          ))}
        </div>

        <div className="pc-body">
          <div className="pc-sec">Account</div>

          <div className="pc-row">
            <div className="ico" aria-hidden="true">
              👤
            </div>
            {editing === "name" ? (
              <>
                <input
                  className="edit-input"
                  value={draft}
                  autoFocus
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void commitEdit();
                    if (e.key === "Escape") setEditing(null);
                  }}
                  aria-label="Display name"
                />
                <button type="button" className="row-btn" disabled={busy} onClick={() => void commitEdit()}>
                  {busy ? "Saving…" : "Save"}
                </button>
              </>
            ) : (
              <>
                <div className="lbl">
                  Display name
                  <small>How you appear in chats</small>
                </div>
                <div className="val">{name}</div>
                <button type="button" className="row-btn" onClick={beginEditName}>
                  Edit
                </button>
              </>
            )}
          </div>

          <div className="pc-row">
            <div className="ico" aria-hidden="true">
              ✉
            </div>
            <div className="lbl">
              Email
              <small>The address you registered with</small>
            </div>
            <div className="val" title={email}>
              {email}
            </div>
          </div>

          <Link href="/signup?mode=face" className="pc-row">
            <div className="ico" aria-hidden="true">
              ◉
            </div>
            <div className="lbl">
              {faceEnrolled ? "Update Face ID" : "Set up Face ID"}
              <small>
                {faceEnrolled
                  ? "Capture a new face to replace the one used for sign-in"
                  : "Not set up yet — enroll to unlock with your face"}
              </small>
            </div>
            <div className="chev" aria-hidden="true">
              ›
            </div>
          </Link>

          <div className="pc-sec">Session</div>

          <button
            type="button"
            className="pc-row"
            onClick={() => {
              logout();
              router.replace("/");
            }}
          >
            <div className="ico" aria-hidden="true">
              ↩
            </div>
            <div className="lbl">Sign out</div>
            <div className="chev" aria-hidden="true">
              ›
            </div>
          </button>

          <button
            type="button"
            className="pc-row danger"
            onClick={() => {
              setError(null);
              setConfirmingDelete(true);
            }}
          >
            <div className="ico" aria-hidden="true">
              🗑
            </div>
            <div className="lbl">
              Delete account
              <small>Permanently removes your account and chats</small>
            </div>
            <div className="chev" aria-hidden="true">
              ›
            </div>
          </button>

          {error && <div className="field-error" style={{ margin: "12px 0 0" }}>{error}</div>}
        </div>
      </div>

      {confirmingDelete && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-title"
          onClick={() => !busy && setConfirmingDelete(false)}
        >
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h4 id="delete-title">Delete your account?</h4>
            <p>
              This permanently deletes your account, conversations, indexed documents, and Face ID
              data from the server. It cannot be undone.
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="btn ghost"
                disabled={busy}
                onClick={() => setConfirmingDelete(false)}
              >
                Keep account
              </button>
              <button
                type="button"
                className="btn danger"
                disabled={busy}
                onClick={() => void confirmDelete()}
              >
                {busy ? "Deleting…" : "Delete everything"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
