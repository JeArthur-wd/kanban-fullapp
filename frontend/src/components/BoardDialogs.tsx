"use client";

import { useState, type FormEvent } from "react";
import { Dialog } from "@/components/Dialog";
import {
  dangerButton,
  errorMessage,
  errorText,
  ghostButton,
  inputClass,
  labelClass,
  outlineButton,
  primaryButton,
} from "@/components/ui";
import type { BoardSummary, BoardTemplate } from "@/lib/api";

const textareaClass = `${inputClass} h-auto resize-none py-2`;

type NewBoardDialogProps = {
  onCreate: (title: string, description: string, template: BoardTemplate) => Promise<void>;
  onClose: () => void;
};

export const NewBoardDialog = ({ onCreate, onClose }: NewBoardDialogProps) => {
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") || "").trim();
    if (!title) {
      setError("Give the board a name.");
      return;
    }
    setIsSaving(true);
    try {
      await onCreate(
        title,
        String(form.get("description") || "").trim(),
        form.get("template") === "sample" ? "sample" : "basic"
      );
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Unable to create the board."));
      setIsSaving(false);
    }
  };

  return (
    <Dialog title="New board" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="new-board-title" className={labelClass}>
            Name
          </label>
          <input
            id="new-board-title"
            name="title"
            maxLength={200}
            placeholder="Product launch"
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="new-board-description" className={labelClass}>
            Description <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea
            id="new-board-description"
            name="description"
            rows={2}
            maxLength={2000}
            className={textareaClass}
          />
        </div>
        <fieldset>
          <legend className={labelClass}>Start with</legend>
          <div className="mt-1.5 grid grid-cols-2 gap-2">
            {[
              { value: "basic", label: "Empty columns", hint: "To do, In progress, Done" },
              { value: "sample", label: "Sample board", hint: "Five columns with example cards" },
            ].map((option) => (
              <label
                key={option.value}
                className="flex cursor-pointer gap-2 rounded-lg border border-line p-2.5 transition-colors hover:border-line-strong has-[:checked]:border-accent has-[:checked]:bg-accent-soft"
              >
                <input
                  type="radio"
                  name="template"
                  value={option.value}
                  defaultChecked={option.value === "basic"}
                  className="mt-0.5 accent-[var(--accent)]"
                />
                <span>
                  <span className="block text-[13px] font-medium text-ink">{option.label}</span>
                  <span className="block text-xs text-muted">{option.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {error ? (
          <p role="alert" className={errorText}>
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={ghostButton}>
            Cancel
          </button>
          <button type="submit" disabled={isSaving} className={primaryButton}>
            Create board
          </button>
        </div>
      </form>
    </Dialog>
  );
};

type BoardSettingsDialogProps = {
  board: BoardSummary;
  onSave: (title: string, description: string) => Promise<void>;
  onDelete: () => Promise<void>;
  onClose: () => void;
};

export const BoardSettingsDialog = ({
  board,
  onSave,
  onDelete,
  onClose,
}: BoardSettingsDialogProps) => {
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const run = async (action: () => Promise<void>, fallback: string) => {
    setIsSaving(true);
    setError(null);
    try {
      await action();
      onClose();
    } catch (err) {
      setError(errorMessage(err, fallback));
      setIsSaving(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const title = String(form.get("title") || "").trim();
    if (!title) {
      setError("Give the board a name.");
      return;
    }
    run(() => onSave(title, String(form.get("description") || "").trim()), "Unable to save the board.");
  };

  return (
    <Dialog title="Board settings" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="board-title" className={labelClass}>
            Name
          </label>
          <input
            id="board-title"
            name="title"
            maxLength={200}
            defaultValue={board.title}
            className={inputClass}
          />
        </div>
        <div>
          <label htmlFor="board-description" className={labelClass}>
            Description
          </label>
          <textarea
            id="board-description"
            name="description"
            rows={3}
            maxLength={2000}
            defaultValue={board.description}
            className={textareaClass}
          />
        </div>
        {error ? (
          <p role="alert" className={errorText}>
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className={ghostButton}>
            Cancel
          </button>
          <button type="submit" disabled={isSaving} className={primaryButton}>
            Save
          </button>
        </div>
      </form>

      <div className="mt-5 border-t border-line pt-4">
        {confirmingDelete ? (
          <div className="space-y-3 rounded-lg bg-danger-soft p-3">
            <p className="text-[13px] text-ink">
              Delete <strong>{board.title}</strong> and its {board.cardCount}{" "}
              {board.cardCount === 1 ? "card" : "cards"}? This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmingDelete(false)}
                className={outlineButton}
              >
                Keep board
              </button>
              <button
                type="button"
                disabled={isSaving}
                onClick={() => run(onDelete, "Unable to delete the board.")}
                className={dangerButton}
              >
                Delete board
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <p className="text-[13px] text-muted">Remove this board and everything on it.</p>
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="h-8 shrink-0 rounded-md px-3 text-[13px] font-medium text-danger transition-colors hover:bg-danger-soft"
            >
              Delete board
            </button>
          </div>
        )}
      </div>
    </Dialog>
  );
};
