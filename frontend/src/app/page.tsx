"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type SetStateAction,
} from "react";
import { ChatSidebar } from "@/components/ChatSidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardMark } from "@/components/icons";
import {
  ApiError,
  createCard,
  deleteCard,
  fetchBoard,
  fetchSession,
  login,
  logout,
  sendChat,
  setUnauthorizedHandler,
  toBoardData,
  updateCard,
  updateColumn,
  type ChatMessage,
} from "@/lib/api";
import { findCardLocation, fromCardId, fromColumnId, type BoardData } from "@/lib/kanban";

// Keep in step with CHAT_HISTORY_MAX_ITEMS and the history content limit on the server.
const CHAT_HISTORY_LIMIT = 20;
const CHAT_CONTENT_LIMIT = 8000;
const BOARD_ERROR_MS = 6000;

const inputClass =
  "mt-1.5 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink transition-colors hover:border-line-strong focus:border-accent";

const Spinner = () => (
  <svg
    className="mx-auto h-6 w-6 motion-safe:animate-spin text-accent"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden
  >
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".2" strokeWidth="3" />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
);

export default function Home() {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isChatSending, setIsChatSending] = useState(false);
  // Only the newest board response may be applied; older ones are dropped.
  const refreshSeq = useRef(0);

  const resetSession = useCallback(() => {
    refreshSeq.current += 1;
    setUsername(null);
    setBoard(null);
    setBoardError(null);
    setChatMessages([]);
    setChatError(null);
  }, []);

  const refreshBoard = useCallback(async () => {
    const seq = ++refreshSeq.current;
    setBoardError(null);
    try {
      const payload = await fetchBoard();
      if (seq === refreshSeq.current) {
        setBoard(toBoardData(payload));
      }
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      if (seq === refreshSeq.current) {
        setBoardError("Unable to load the board from the server.");
      }
    }
  }, []);

  // Put the board back in sync with the server, then say what went wrong. The message is
  // set after the refresh because the refresh clears any earlier message.
  const recoverFrom = useCallback(
    async (err: unknown, message: string) => {
      if (process.env.NODE_ENV === "development") console.error(err);
      await refreshBoard();
      setBoardError(message);
    },
    [refreshBoard]
  );

  const handleBoardChange = useCallback(
    (updater: SetStateAction<BoardData>) => {
      setBoard((prev) => {
        if (!prev) {
          return prev;
        }
        return typeof updater === "function" ? updater(prev) : updater;
      });
    },
    []
  );

  useEffect(() => {
    setUnauthorizedHandler(() => {
      resetSession();
      setError("Your session has ended. Please sign in again.");
    });
    return () => setUnauthorizedHandler(null);
  }, [resetSession]);

  useEffect(() => {
    let cancelled = false;
    fetchSession()
      .then((session) => {
        if (cancelled) return;
        setUsername(session.username);
        refreshBoard();
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setSessionChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshBoard]);

  useEffect(() => {
    if (!boardError || !board) return;
    const timer = setTimeout(() => setBoardError(null), BOARD_ERROR_MS);
    return () => clearTimeout(timer);
  }, [boardError, board]);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const enteredUsername = String(formData.get("username") || "").trim();
    const enteredPassword = String(formData.get("password") || "");

    try {
      const session = await login(enteredUsername, enteredPassword);
      setError(null);
      form.reset();
      setUsername(session.username);
      refreshBoard();
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Incorrect username or password.");
      } else if (err instanceof ApiError && err.detail) {
        setError(err.detail);
      } else {
        setError("Unable to sign in right now. Please try again.");
      }
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // The local state is cleared either way; an expired session needs no server call.
    }
    resetSession();
    setError(null);
  };

  const handleRenameColumn = async (columnId: string, title: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to save column changes.");
      return;
    }
    try {
      await updateColumn(columnIdNumber, { title });
    } catch (err) {
      await recoverFrom(err, "Unable to save column changes.");
    }
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to add the card.");
      return;
    }
    try {
      await createCard({
        column_id: columnIdNumber,
        title,
        details: details || "No details yet.",
      });
      refreshBoard();
    } catch (err) {
      await recoverFrom(err, "Unable to add the card.");
    }
  };

  const handleDeleteCard = async (columnId: string, cardId: string) => {
    const cardIdNumber = Number(fromCardId(cardId));
    if (Number.isNaN(cardIdNumber)) {
      return;
    }
    try {
      await deleteCard(cardIdNumber);
      refreshBoard();
    } catch (err) {
      await recoverFrom(err, "Unable to remove the card.");
    }
  };

  const handleMoveCard = async (activeId: string, nextColumns: BoardData["columns"]) => {
    const location = findCardLocation(nextColumns, activeId);
    if (!location) {
      return;
    }
    const cardIdNumber = Number(fromCardId(activeId));
    const columnIdNumber = Number(fromColumnId(location.columnId));
    if (Number.isNaN(cardIdNumber) || Number.isNaN(columnIdNumber)) {
      return;
    }
    try {
      await updateCard(cardIdNumber, {
        column_id: columnIdNumber,
        position: location.index,
      });
      refreshBoard();
    } catch (err) {
      await recoverFrom(err, "Unable to move the card.");
    }
  };

  const handleSendChat = async (message: string) => {
    setChatError(null);
    setIsChatSending(true);
    const userMessage: ChatMessage = { role: "user", content: message };
    const history = chatMessages
      .filter((item) => !item.isError)
      .slice(-CHAT_HISTORY_LIMIT)
      .map(({ role, content }) => ({ role, content: content.slice(0, CHAT_CONTENT_LIMIT) }));
    setChatMessages((prev) => [...prev, userMessage]);

    try {
      const response = await sendChat({
        message,
        history,
        apply_updates: true,
      });
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.response,
      };
      setChatMessages((prev) => [...prev, assistantMessage]);
      if (response.board) {
        refreshSeq.current += 1;
        setBoard(toBoardData(response.board));
      }
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      const text =
        err instanceof ApiError && err.detail
          ? err.detail
          : "Unable to reach the assistant right now.";
      setChatError(text);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again.", isError: true },
      ]);
    } finally {
      setIsChatSending(false);
    }
  };

  if (!sessionChecked) {
    return (
      <main className="grid min-h-screen place-items-center px-4">
        <section className="text-center" role="status">
          <Spinner />
          <h1 className="mt-4 text-base font-semibold text-ink">Loading</h1>
        </section>
      </main>
    );
  }

  if (!username) {
    return (
      <main className="grid min-h-screen place-items-center px-4 py-12">
        <section className="w-full max-w-[400px] rounded-xl border border-line bg-surface p-8 shadow-panel">
          <div className="flex items-center gap-2.5">
            <BoardMark />
            <span className="text-[15px] font-semibold tracking-tight text-ink">
              Kanban Studio
            </span>
          </div>
          <h1 className="mt-8 text-2xl font-semibold tracking-tight text-ink">
            Welcome back
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Sign in to continue to your Kanban board. Use the demo credentials to explore the MVP.
          </p>

          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            <div>
              <label htmlFor="username" className="text-[13px] font-medium text-ink">
                Username
              </label>
              <input
                id="username"
                name="username"
                placeholder="user"
                aria-label="Username"
                autoComplete="username"
                className={inputClass}
                required
              />
            </div>
            <div>
              <label htmlFor="password" className="text-[13px] font-medium text-ink">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                placeholder="password"
                aria-label="Password"
                autoComplete="current-password"
                className={inputClass}
                required
              />
            </div>
            {error ? (
              <p role="alert" className="text-[13px] font-medium text-danger">
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              className="h-10 w-full rounded-lg bg-accent text-sm font-medium text-white transition-colors hover:bg-accent-strong"
            >
              Sign in
            </button>
          </form>
          <p className="mt-5 rounded-lg bg-ground px-3 py-2.5 text-[13px] text-muted">
            Demo credentials: user / password
          </p>
        </section>
      </main>
    );
  }

  if (!board) {
    if (boardError) {
      return (
        <main className="grid min-h-screen place-items-center px-4">
          <section className="text-center">
            <h1 className="text-base font-semibold text-ink">Could not load your board</h1>
            <p role="alert" className="mt-1 text-sm text-danger">
              {boardError}
            </p>
            <button
              type="button"
              onClick={refreshBoard}
              className="mt-4 h-9 rounded-lg bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-strong"
            >
              Try again
            </button>
          </section>
        </main>
      );
    }
    return (
      <main className="grid min-h-screen place-items-center px-4">
        <section className="text-center" role="status">
          <Spinner />
          <h1 className="mt-4 text-base font-semibold text-ink">Loading your board</h1>
          <p className="mt-1 text-sm text-muted">
            Fetching the latest updates from the server.
          </p>
        </section>
      </main>
    );
  }

  return (
    <>
      <KanbanBoard
        board={board}
        onBoardChange={handleBoardChange}
        onLogout={handleLogout}
        username={username}
        onRenameColumn={handleRenameColumn}
        onAddCard={handleAddCard}
        onDeleteCard={handleDeleteCard}
        onMoveCard={handleMoveCard}
        sidebar={(
          <ChatSidebar
            messages={chatMessages}
            onSend={handleSendChat}
            isSending={isChatSending}
            error={chatError}
          />
        )}
      />
      {boardError ? (
        <div
          role="alert"
          className="fixed bottom-4 left-1/2 z-30 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-lg border border-danger/20 bg-danger-soft px-4 py-3 text-sm font-medium text-danger shadow-lift"
        >
          {boardError}
        </div>
      ) : null}
    </>
  );
}
