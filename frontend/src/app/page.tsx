"use client";

import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type SetStateAction,
} from "react";
import { ChatSidebar } from "@/components/ChatSidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardMark } from "@/components/icons";
import {
  fetchBoard,
  createCard,
  deleteCard,
  sendChat,
  toBoardData,
  updateCard,
  updateColumn,
  type ChatMessage,
} from "@/lib/api";
import { findCardLocation, fromCardId, fromColumnId, type BoardData } from "@/lib/kanban";

const CREDENTIALS = { username: "user", password: "password" };

const inputClass =
  "mt-1.5 h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink transition-colors hover:border-line-strong focus:border-accent";

export default function Home() {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string>(CREDENTIALS.username);
  const [error, setError] = useState<string | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isChatSending, setIsChatSending] = useState(false);

  const refreshBoard = useCallback(async () => {
    setBoardError(null);
    try {
      const payload = await fetchBoard(username);
      setBoard(toBoardData(payload));
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to load the board from the server.");
    }
  }, [username]);

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

  const handleLogin = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();

    if (username === CREDENTIALS.username && password === CREDENTIALS.password) {
      setUsername(username);
      setIsAuthenticated(true);
      setError(null);
      event.currentTarget.reset();
      return;
    }

    setError("Incorrect username or password.");
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setBoard(null);
    setBoardError(null);
    setChatMessages([]);
    setChatError(null);
  };

  useEffect(() => {
    if (isAuthenticated) {
      refreshBoard();
    }
  }, [isAuthenticated, refreshBoard]);

  const handleRenameColumn = async (columnId: string, title: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to save column changes.");
      return;
    }
    try {
      await updateColumn(columnIdNumber, { title }, username);
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to save column changes.");
      refreshBoard();
    }
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to add the card.");
      return;
    }
    try {
      await createCard(
        {
          column_id: columnIdNumber,
          title,
          details: details || "No details yet.",
        },
        username
      );
      refreshBoard();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to add the card.");
      refreshBoard();
    }
  };

  const handleDeleteCard = async (columnId: string, cardId: string) => {
    const cardIdNumber = Number(fromCardId(cardId));
    if (Number.isNaN(cardIdNumber)) {
      return;
    }
    try {
      await deleteCard(cardIdNumber, username);
      refreshBoard();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to remove the card.");
      refreshBoard();
    }
  };

  const handleMoveCard = async (
    activeId: string,
    _overId: string,
    nextColumns: BoardData["columns"]
  ) => {
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
      await updateCard(
        cardIdNumber,
        {
          column_id: columnIdNumber,
          position: location.index,
        },
        username
      );
      refreshBoard();
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardError("Unable to move the card.");
      refreshBoard();
    }
  };

  const welcomeCopy =
    "Sign in to continue to your Kanban board. Use the demo credentials to explore the MVP.";

  const handleSendChat = async (message: string) => {
    setChatError(null);
    setIsChatSending(true);
    const userMessage: ChatMessage = { role: "user", content: message };
    const history = [...chatMessages];
    setChatMessages((prev) => [...prev, userMessage]);

    try {
      const response = await sendChat(
        {
          message,
          history,
          apply_updates: true,
        },
        username
      );
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.response,
      };
      setChatMessages((prev) => [...prev, assistantMessage]);
      if (response.board) {
        setBoard(toBoardData(response.board));
      }
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setChatError("Unable to reach the assistant right now.");
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setIsChatSending(false);
    }
  };

  if (!isAuthenticated) {
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
          <p className="mt-2 text-sm leading-6 text-muted">{welcomeCopy}</p>

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
    return (
      <main className="grid min-h-screen place-items-center px-4">
        <section className="text-center" role="status">
          <svg
            className="mx-auto h-6 w-6 motion-safe:animate-spin text-accent"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden
          >
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".2" strokeWidth="3" />
            <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
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
