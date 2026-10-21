"use client";

import { useCallback, useEffect, useRef, useState, type SetStateAction } from "react";
import { AccountDialog } from "@/components/AccountDialog";
import { AppHeader } from "@/components/AppHeader";
import { AuthScreen } from "@/components/AuthScreen";
import { NewBoardDialog } from "@/components/BoardDialogs";
import { BoardSwitcher } from "@/components/BoardSwitcher";
import { ChatSidebar } from "@/components/ChatSidebar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { PlusIcon } from "@/components/icons";
import { primaryButton } from "@/components/ui";
import {
  ApiError,
  createBoard,
  createCard,
  deleteBoard,
  deleteCard,
  fetchBoard,
  fetchSession,
  listBoards,
  logout,
  sendChat,
  setUnauthorizedHandler,
  toBoardData,
  updateBoard,
  updateCard,
  updateColumn,
  type BoardSummary,
  type BoardTemplate,
  type ChatMessage,
  type Session,
} from "@/lib/api";
import { findCardLocation, fromCardId, fromColumnId, type BoardData } from "@/lib/kanban";

// Keep in step with CHAT_HISTORY_MAX_ITEMS and the history content limit on the server.
const CHAT_HISTORY_LIMIT = 20;
const CHAT_CONTENT_LIMIT = 8000;
const BOARD_ERROR_MS = 6000;
const LAST_BOARD_KEY = "kanban:lastBoard";

// Remembering the last board is a convenience; storage can be unavailable.
const readLastBoard = () => {
  try {
    return window.localStorage.getItem(LAST_BOARD_KEY);
  } catch {
    return null;
  }
};

const rememberBoard = (boardId: string) => {
  try {
    window.localStorage.setItem(LAST_BOARD_KEY, boardId);
  } catch {
    // Ignored: the first board is opened instead next time.
  }
};

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

const CenteredStatus = ({ title, detail }: { title: string; detail?: string }) => (
  <main className="grid flex-1 place-items-center px-4 py-16">
    <section className="text-center" role="status">
      <Spinner />
      <h2 className="mt-4 text-base font-semibold text-ink">{title}</h2>
      {detail ? <p className="mt-1 text-sm text-muted">{detail}</p> : null}
    </section>
  </main>
);

const RetryPanel = ({ title, error, onRetry }: { title: string; error: string; onRetry: () => void }) => (
  <main className="grid flex-1 place-items-center px-4 py-16">
    <section className="text-center">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <p role="alert" className="mt-1 text-sm text-danger">
        {error}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 h-9 rounded-lg bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-strong"
      >
        Try again
      </button>
    </section>
  </main>
);

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [boards, setBoards] = useState<BoardSummary[] | null>(null);
  const [boardsError, setBoardsError] = useState<string | null>(null);
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null);
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isChatSending, setIsChatSending] = useState(false);
  const [dialog, setDialog] = useState<"account" | "first-board" | null>(null);
  // The board that requests are for. A ref, so callbacks made earlier see the current board.
  const activeBoardRef = useRef<string | null>(null);
  // Only the newest board response may be applied; older ones are dropped.
  const refreshSeq = useRef(0);

  const resetSession = useCallback(() => {
    refreshSeq.current += 1;
    activeBoardRef.current = null;
    setSession(null);
    setBoards(null);
    setBoardsError(null);
    setActiveBoardId(null);
    setBoard(null);
    setBoardError(null);
    setChatMessages([]);
    setChatError(null);
    setDialog(null);
  }, []);

  const refreshBoard = useCallback(async () => {
    const boardId = activeBoardRef.current;
    if (!boardId) return;
    const seq = ++refreshSeq.current;
    setBoardError(null);
    try {
      const payload = await fetchBoard(boardId);
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

  // Switch to a board (or to none). The chat belongs to the board, so it starts empty.
  const openBoard = useCallback(
    (boardId: string | null) => {
      refreshSeq.current += 1;
      activeBoardRef.current = boardId;
      setActiveBoardId(boardId);
      setBoard(null);
      setBoardError(null);
      setChatMessages([]);
      setChatError(null);
      if (boardId) {
        rememberBoard(boardId);
        refreshBoard();
      }
    },
    [refreshBoard]
  );

  const loadBoards = useCallback(async () => {
    setBoardsError(null);
    try {
      const list = await listBoards();
      setBoards(list);
      return list;
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      setBoardsError("Unable to load your boards from the server.");
      return null;
    }
  }, []);

  const startSession = useCallback(
    async (next: Session) => {
      setSession(next);
      setNotice(null);
      const list = await loadBoards();
      if (!list) return;
      const last = readLastBoard();
      openBoard((list.find((item) => item.id === last) ?? list[0])?.id ?? null);
    },
    [loadBoards, openBoard]
  );

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

  const handleBoardChange = useCallback((updater: SetStateAction<BoardData>) => {
    setBoard((prev) => {
      if (!prev) {
        return prev;
      }
      return typeof updater === "function" ? updater(prev) : updater;
    });
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      resetSession();
      setNotice("Your session has ended. Please sign in again.");
    });
    return () => setUnauthorizedHandler(null);
  }, [resetSession]);

  useEffect(() => {
    let cancelled = false;
    fetchSession()
      .then((current) => {
        if (!cancelled) startSession(current);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setSessionChecked(true);
      });
    return () => {
      cancelled = true;
    };
  }, [startSession]);

  useEffect(() => {
    if (!boardError || !board) return;
    const timer = setTimeout(() => setBoardError(null), BOARD_ERROR_MS);
    return () => clearTimeout(timer);
  }, [boardError, board]);

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // The local state is cleared either way; an expired session needs no server call.
    }
    resetSession();
    setNotice(null);
  };

  const handleCreateBoard = async (title: string, description: string, template: BoardTemplate) => {
    const { id } = await createBoard({ title, description, template });
    await loadBoards();
    openBoard(id);
  };

  const handleUpdateBoard = async (boardId: string, title: string, description: string) => {
    await updateBoard(boardId, { title, description });
    setBoards((prev) =>
      prev ? prev.map((item) => (item.id === boardId ? { ...item, title, description } : item)) : prev
    );
  };

  const handleDeleteBoard = async (boardId: string) => {
    await deleteBoard(boardId);
    const list = await loadBoards();
    if (boardId === activeBoardRef.current) {
      openBoard(list?.[0]?.id ?? null);
    }
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
      await createCard({ column_id: columnIdNumber, title, details });
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
    const boardId = activeBoardRef.current;
    if (!boardId) return;
    setChatError(null);
    setIsChatSending(true);
    const userMessage: ChatMessage = { role: "user", content: message };
    const history = chatMessages
      .filter((item) => !item.isError)
      .slice(-CHAT_HISTORY_LIMIT)
      .map(({ role, content }) => ({ role, content: content.slice(0, CHAT_CONTENT_LIMIT) }));
    setChatMessages((prev) => [...prev, userMessage]);

    try {
      const response = await sendChat(boardId, {
        message,
        history,
        apply_updates: true,
      });
      // The user may have switched boards while the assistant was answering.
      if (boardId !== activeBoardRef.current) return;
      setChatMessages((prev) => [...prev, { role: "assistant", content: response.response }]);
      if (response.board) {
        refreshSeq.current += 1;
        setBoard(toBoardData(response.board));
      }
    } catch (err) {
      if (process.env.NODE_ENV === "development") console.error(err);
      if (boardId !== activeBoardRef.current) return;
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
      <div className="flex min-h-screen flex-col">
        <CenteredStatus title="Loading" />
      </div>
    );
  }

  if (!session) {
    return <AuthScreen onSignedIn={startSession} notice={notice} />;
  }

  const renderContent = () => {
    if (!boards) {
      return boardsError ? (
        <RetryPanel title="Could not load your boards" error={boardsError} onRetry={() => startSession(session)} />
      ) : (
        <CenteredStatus title="Loading your boards" />
      );
    }
    if (boards.length === 0) {
      return (
        <main className="grid flex-1 place-items-center px-4 py-16">
          <section className="max-w-sm text-center">
            <h2 className="text-base font-semibold text-ink">No boards yet</h2>
            <p className="mt-1 text-sm text-muted">
              Create a board to start planning work with your columns and cards.
            </p>
            <button
              type="button"
              onClick={() => setDialog("first-board")}
              className={`${primaryButton} mt-4 inline-flex items-center gap-1.5`}
            >
              <PlusIcon width={14} height={14} />
              Create a board
            </button>
          </section>
        </main>
      );
    }
    if (!board) {
      return boardError ? (
        <RetryPanel title="Could not load your board" error={boardError} onRetry={refreshBoard} />
      ) : (
        <CenteredStatus
          title="Loading your board"
          detail="Fetching the latest updates from the server."
        />
      );
    }
    return (
      <KanbanBoard
        board={board}
        onBoardChange={handleBoardChange}
        onRenameColumn={handleRenameColumn}
        onAddCard={handleAddCard}
        onDeleteCard={handleDeleteCard}
        onMoveCard={handleMoveCard}
        sidebar={
          <ChatSidebar
            messages={chatMessages}
            onSend={handleSendChat}
            isSending={isChatSending}
            error={chatError}
          />
        }
      />
    );
  };

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader
        boardControls={
          boards && boards.length > 0 ? (
            <BoardSwitcher
              boards={boards}
              activeBoardId={activeBoardId}
              onSelect={openBoard}
              onCreate={handleCreateBoard}
              onUpdate={handleUpdateBoard}
              onDelete={handleDeleteBoard}
              onOpen={loadBoards}
            />
          ) : null
        }
        accountLabel={session.displayName || session.username}
        onOpenAccount={() => setDialog("account")}
        onLogout={handleLogout}
      />
      {renderContent()}
      {board && boardError ? (
        <div
          role="alert"
          className="fixed bottom-4 left-1/2 z-30 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-lg border border-danger/20 bg-danger-soft px-4 py-3 text-sm font-medium text-danger shadow-lift"
        >
          {boardError}
        </div>
      ) : null}
      {dialog === "account" ? (
        <AccountDialog
          session={session}
          onSessionChange={setSession}
          onAccountDeleted={() => {
            resetSession();
            setNotice("Your account has been deleted.");
          }}
          onClose={() => setDialog(null)}
        />
      ) : null}
      {dialog === "first-board" ? (
        <NewBoardDialog onCreate={handleCreateBoard} onClose={() => setDialog(null)} />
      ) : null}
    </div>
  );
}
