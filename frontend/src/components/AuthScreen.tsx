"use client";

import { useState, type FormEvent } from "react";
import { BoardMark } from "@/components/icons";
import { errorMessage, labelClass } from "@/components/ui";
import { ApiError, login, register, type Session } from "@/lib/api";

const inputClass =
  "mt-1.5 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink transition-colors hover:border-line-strong focus:border-accent";

type AuthScreenProps = {
  onSignedIn: (session: Session) => void;
  // Shown above the form, for example when a session has just ended.
  notice?: string | null;
};

export const AuthScreen = ({ onSignedIn, notice }: AuthScreenProps) => {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSignUp = mode === "signup";

  const switchMode = () => {
    setMode(isSignUp ? "signin" : "signup");
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") || "").trim();
    const password = String(form.get("password") || "");
    setIsSubmitting(true);
    try {
      if (isSignUp) {
        if (password !== String(form.get("confirm") || "")) {
          setError("The passwords do not match.");
          return;
        }
        onSignedIn(await register(username, password, String(form.get("displayName") || "").trim()));
      } else {
        onSignedIn(await login(username, password));
      }
    } catch (err) {
      if (!isSignUp && err instanceof ApiError && err.status === 401) {
        setError("Incorrect username or password.");
      } else if (err instanceof ApiError && err.status === 422 && !err.detail) {
        setError("Use at least 8 characters for the password.");
      } else {
        setError(
          errorMessage(
            err,
            isSignUp
              ? "Unable to create the account right now. Please try again."
              : "Unable to sign in right now. Please try again."
          )
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const shownError = error ?? notice;

  return (
    <main className="grid min-h-screen place-items-center px-4 py-12">
      <section className="w-full max-w-[400px] rounded-xl border border-line bg-surface p-8 shadow-panel">
        <div className="flex items-center gap-2.5">
          <BoardMark />
          <span className="text-[15px] font-semibold tracking-tight text-ink">Kanban Studio</span>
        </div>
        <h1 className="mt-8 text-2xl font-semibold tracking-tight text-ink">
          {isSignUp ? "Create your account" : "Welcome back"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          {isSignUp
            ? "Your account starts with one sample board. Add as many boards as you need."
            : "Sign in to continue to your boards."}
        </p>

        <form key={mode} onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="username" className={labelClass}>
              Username
            </label>
            <input
              id="username"
              name="username"
              placeholder={isSignUp ? "Pick a username" : "user"}
              autoComplete="username"
              className={inputClass}
              required
            />
            {isSignUp ? (
              <p className="mt-1 text-xs text-muted">
                3 to 32 characters: letters, numbers, dots, dashes, underscores.
              </p>
            ) : null}
          </div>
          {isSignUp ? (
            <div>
              <label htmlFor="displayName" className={labelClass}>
                Name <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="displayName"
                name="displayName"
                placeholder="How your name is shown"
                autoComplete="name"
                maxLength={80}
                className={inputClass}
              />
            </div>
          ) : null}
          <div>
            <label htmlFor="password" className={labelClass}>
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              placeholder={isSignUp ? "At least 8 characters" : "password"}
              autoComplete={isSignUp ? "new-password" : "current-password"}
              minLength={isSignUp ? 8 : undefined}
              className={inputClass}
              required
            />
          </div>
          {isSignUp ? (
            <div>
              <label htmlFor="confirm" className={labelClass}>
                Confirm password
              </label>
              <input
                id="confirm"
                name="confirm"
                type="password"
                placeholder="Type it again"
                autoComplete="new-password"
                className={inputClass}
                required
              />
            </div>
          ) : null}
          {shownError ? (
            <p role="alert" className="text-[13px] font-medium text-danger">
              {shownError}
            </p>
          ) : null}
          <button
            type="submit"
            disabled={isSubmitting}
            className="h-10 w-full rounded-lg bg-accent text-sm font-medium text-white transition-colors hover:bg-accent-strong disabled:opacity-60"
          >
            {isSignUp ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-[13px] text-muted">
          {isSignUp ? "Already have an account?" : "New here?"}{" "}
          <button
            type="button"
            onClick={switchMode}
            className="font-medium text-accent hover:text-accent-strong"
          >
            {isSignUp ? "Sign in" : "Create an account"}
          </button>
        </p>
        {isSignUp ? null : (
          <p className="mt-4 rounded-lg bg-ground px-3 py-2.5 text-[13px] text-muted">
            Demo account: user / password
          </p>
        )}
      </section>
    </main>
  );
};
