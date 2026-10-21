"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import { Dialog } from "@/components/Dialog";
import {
  dangerButton,
  errorMessage,
  errorText,
  inputClass,
  labelClass,
  outlineButton,
  primaryButton,
} from "@/components/ui";
import {
  changePassword,
  deleteAccount,
  updateProfile,
  type Session,
} from "@/lib/api";

type Status = { kind: "ok" | "error"; text: string } | null;

const StatusLine = ({ status }: { status: Status }) =>
  status ? (
    <p
      role={status.kind === "error" ? "alert" : "status"}
      className={status.kind === "error" ? errorText : "text-[13px] font-medium text-[var(--dot-done)]"}
    >
      {status.text}
    </p>
  ) : null;

const Section = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="border-t border-line pt-4 first:border-t-0 first:pt-0">
    <h3 className="mb-3 text-[13px] font-semibold text-ink">{title}</h3>
    {children}
  </section>
);

type AccountDialogProps = {
  session: Session;
  onSessionChange: (session: Session) => void;
  onAccountDeleted: () => void;
  onClose: () => void;
};

export const AccountDialog = ({
  session,
  onSessionChange,
  onAccountDeleted,
  onClose,
}: AccountDialogProps) => {
  const [profileStatus, setProfileStatus] = useState<Status>(null);
  const [passwordStatus, setPasswordStatus] = useState<Status>(null);
  const [deleteStatus, setDeleteStatus] = useState<Status>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const displayName = String(new FormData(event.currentTarget).get("displayName") || "");
    setBusy(true);
    try {
      onSessionChange(await updateProfile(displayName.trim()));
      setProfileStatus({ kind: "ok", text: "Saved." });
    } catch (err) {
      setProfileStatus({ kind: "error", text: errorMessage(err, "Unable to save your name.") });
    } finally {
      setBusy(false);
    }
  };

  const handlePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const next = String(form.get("newPassword") || "");
    if (next !== String(form.get("confirmPassword") || "")) {
      setPasswordStatus({ kind: "error", text: "The new passwords do not match." });
      return;
    }
    setBusy(true);
    try {
      await changePassword(String(form.get("currentPassword") || ""), next);
      formElement.reset();
      setPasswordStatus({
        kind: "ok",
        text: "Password changed. Other devices have been signed out.",
      });
    } catch (err) {
      setPasswordStatus({
        kind: "error",
        text: errorMessage(err, "Unable to change the password."),
      });
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      await deleteAccount(String(new FormData(event.currentTarget).get("deletePassword") || ""));
      onAccountDeleted();
    } catch (err) {
      setDeleteStatus({ kind: "error", text: errorMessage(err, "Unable to delete the account.") });
      setBusy(false);
    }
  };

  return (
    <Dialog title="Account settings" onClose={onClose}>
      <div className="space-y-5">
        <Section title="Profile">
          <form onSubmit={handleProfile} className="space-y-3">
            <div>
              <p className={labelClass}>Username</p>
              <p className="mt-1 text-sm text-muted">{session.username}</p>
            </div>
            <div>
              <label htmlFor="account-name" className={labelClass}>
                Name
              </label>
              <input
                id="account-name"
                name="displayName"
                defaultValue={session.displayName}
                maxLength={80}
                placeholder="How your name is shown"
                className={inputClass}
              />
            </div>
            <StatusLine status={profileStatus} />
            <div className="flex justify-end">
              <button type="submit" disabled={busy} className={primaryButton}>
                Save name
              </button>
            </div>
          </form>
        </Section>

        <Section title="Password">
          <form onSubmit={handlePassword} className="space-y-3">
            <div>
              <label htmlFor="current-password" className={labelClass}>
                Current password
              </label>
              <input
                id="current-password"
                name="currentPassword"
                type="password"
                autoComplete="current-password"
                required
                className={inputClass}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="new-password" className={labelClass}>
                  New password
                </label>
                <input
                  id="new-password"
                  name="newPassword"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="confirm-password" className={labelClass}>
                  Confirm new password
                </label>
                <input
                  id="confirm-password"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  className={inputClass}
                />
              </div>
            </div>
            <StatusLine status={passwordStatus} />
            <div className="flex justify-end">
              <button type="submit" disabled={busy} className={outlineButton}>
                Change password
              </button>
            </div>
          </form>
        </Section>

        <Section title="Delete account">
          {confirmingDelete ? (
            <form onSubmit={handleDelete} className="space-y-3 rounded-lg bg-danger-soft p-3">
              <p className="text-[13px] text-ink">
                This deletes your account and all of your boards. It cannot be undone.
              </p>
              <div>
                <label htmlFor="delete-password" className={labelClass}>
                  Enter your password to confirm
                </label>
                <input
                  id="delete-password"
                  name="deletePassword"
                  type="password"
                  autoComplete="current-password"
                  required
                  className={inputClass}
                />
              </div>
              <StatusLine status={deleteStatus} />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setConfirmingDelete(false)}
                  className={outlineButton}
                >
                  Keep account
                </button>
                <button type="submit" disabled={busy} className={dangerButton}>
                  Delete account
                </button>
              </div>
            </form>
          ) : (
            <div className="flex items-center justify-between gap-3">
              <p className="text-[13px] text-muted">Remove your account and all of its boards.</p>
              <button
                type="button"
                onClick={() => setConfirmingDelete(true)}
                className="h-8 shrink-0 rounded-md px-3 text-[13px] font-medium text-danger transition-colors hover:bg-danger-soft"
              >
                Delete account
              </button>
            </div>
          )}
        </Section>
      </div>
    </Dialog>
  );
};
