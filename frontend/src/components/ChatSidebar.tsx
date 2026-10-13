"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatMessage } from "@/lib/api";
import { SendIcon, SparkIcon } from "@/components/icons";

const initialFormState = { message: "" };

type ChatSidebarProps = {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isSending?: boolean;
  error?: string | null;
};

export const ChatSidebar = ({
  messages,
  onSend,
  isSending = false,
  error,
}: ChatSidebarProps) => {
  const [formState, setFormState] = useState(initialFormState);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [messages, isSending]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = formState.message.trim();
    if (!trimmed || isSending) {
      return;
    }
    onSend(trimmed);
    setFormState(initialFormState);
  };

  return (
    <aside className="flex h-[34rem] flex-col overflow-hidden rounded-xl border border-line bg-surface shadow-panel lg:h-[calc(100dvh-6rem)] lg:max-h-[860px]">
      <div className="flex items-center gap-2 border-b border-line px-4 py-3">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-accent-soft text-accent">
          <SparkIcon width={14} height={14} />
        </span>
        <h2 className="text-sm font-semibold text-ink">AI assistant</h2>
      </div>

      <div
        ref={listRef}
        className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <div className="my-auto px-2 text-center">
            <p className="text-[13px] leading-5 text-muted">
              Ask the assistant to create, move, or update cards.
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "message-in max-w-[85%] self-end whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-accent px-3 py-2 text-sm leading-5 text-white"
                  : "message-in max-w-[90%] self-start whitespace-pre-wrap break-words rounded-2xl rounded-bl-md bg-well px-3 py-2 text-sm leading-5 text-ink"
              }
            >
              {message.content}
            </div>
          ))
        )}
        {isSending ? (
          <div
            role="status"
            className="message-in flex items-center gap-2 self-start rounded-2xl rounded-bl-md bg-well px-3.5 py-3"
          >
            <span className="text-xs text-muted">Working on your board</span>
            {[0, 1, 2].map((dot) => (
              <span
                key={dot}
                className="thinking-dot h-1.5 w-1.5 rounded-full bg-muted"
                style={{ animationDelay: `${dot * 160}ms` }}
                aria-hidden
              />
            ))}
          </div>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="px-4 pb-2 text-xs font-medium text-danger">
          {error}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="border-t border-line p-3">
        <div className="rounded-lg border border-line bg-surface transition-colors focus-within:border-accent hover:border-line-strong">
          <textarea
            value={formState.message}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, message: event.target.value }))
            }
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Ask the assistant"
            rows={2}
            className="block w-full resize-none rounded-lg bg-transparent px-3 pt-2.5 text-sm leading-5 text-ink outline-none"
            aria-label="Chat message"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-2 pt-1">
            <span className="px-1 text-xs text-muted">Shift + Enter for a new line</span>
            <button
              type="submit"
              disabled={isSending}
              className="flex h-8 items-center gap-1.5 rounded-md bg-accent px-3 text-[13px] font-medium text-white transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50"
            >
              <SendIcon width={14} height={14} />
              {isSending ? "Sending" : "Send"}
            </button>
          </div>
        </div>
      </form>
    </aside>
  );
};
