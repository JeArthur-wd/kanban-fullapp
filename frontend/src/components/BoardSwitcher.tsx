"use client";

import { useCallback, useRef, useState } from "react";
import clsx from "clsx";
import { BoardSettingsDialog, NewBoardDialog } from "@/components/BoardDialogs";
import { CheckIcon, ChevronDownIcon, PlusIcon, SettingsIcon } from "@/components/icons";
import { useDismiss } from "@/components/useDismiss";
import type { BoardSummary, BoardTemplate } from "@/lib/api";

type BoardSwitcherProps = {
  boards: BoardSummary[];
  activeBoardId: string | null;
  onSelect: (boardId: string) => void;
  onCreate: (title: string, description: string, template: BoardTemplate) => Promise<void>;
  onUpdate: (boardId: string, title: string, description: string) => Promise<void>;
  onDelete: (boardId: string) => Promise<void>;
  // Called when the menu opens, so card counts can be refreshed.
  onOpen?: () => void;
};

export const BoardSwitcher = ({
  boards,
  activeBoardId,
  onSelect,
  onCreate,
  onUpdate,
  onDelete,
  onOpen,
}: BoardSwitcherProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [dialog, setDialog] = useState<"new" | "settings" | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setIsOpen(false), []);
  useDismiss(containerRef, isOpen, close);

  const active = boards.find((board) => board.id === activeBoardId) ?? null;

  const openDialog = (kind: "new" | "settings") => {
    setIsOpen(false);
    setDialog(kind);
  };

  return (
    <div ref={containerRef} className="relative flex min-w-0 items-center gap-1">
      <button
        type="button"
        onClick={() => {
          if (!isOpen) onOpen?.();
          setIsOpen((open) => !open);
        }}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        className="flex h-8 min-w-0 items-center gap-1.5 rounded-md px-2 text-[13px] font-medium text-ink transition-colors hover:bg-well"
      >
        <span className="truncate">{active ? active.title : "Boards"}</span>
        <ChevronDownIcon width={14} height={14} className="shrink-0 text-muted" />
        <span className="sr-only">Switch board</span>
      </button>
      {active ? (
        <button
          type="button"
          onClick={() => openDialog("settings")}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-muted transition-colors hover:bg-well hover:text-ink"
          aria-label="Board settings"
          title="Board settings"
        >
          <SettingsIcon width={15} height={15} />
        </button>
      ) : null}

      {isOpen ? (
        <div
          role="menu"
          aria-label="Boards"
          className="absolute left-0 top-10 z-30 w-72 rounded-xl border border-line bg-surface p-1.5 shadow-lift"
        >
          <p className="px-2 pb-1 pt-1.5 text-xs font-medium text-muted">Your boards</p>
          <div className="max-h-72 overflow-y-auto">
            {boards.map((board) => (
              <button
                key={board.id}
                type="button"
                role="menuitemradio"
                aria-checked={board.id === activeBoardId}
                onClick={() => {
                  setIsOpen(false);
                  if (board.id !== activeBoardId) onSelect(board.id);
                }}
                className={clsx(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-well",
                  board.id === activeBoardId && "bg-accent-soft hover:bg-accent-soft"
                )}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-medium text-ink">
                    {board.title}
                  </span>
                  <span className="tabular block text-xs text-muted">
                    {board.cardCount} {board.cardCount === 1 ? "card" : "cards"}
                  </span>
                </span>
                {board.id === activeBoardId ? (
                  <CheckIcon width={14} height={14} className="shrink-0 text-accent" />
                ) : null}
              </button>
            ))}
          </div>
          <div className="mt-1 border-t border-line pt-1">
            <button
              type="button"
              role="menuitem"
              onClick={() => openDialog("new")}
              className="flex h-8 w-full items-center gap-2 rounded-md px-2 text-[13px] font-medium text-ink transition-colors hover:bg-well"
            >
              <PlusIcon width={14} height={14} className="text-muted" />
              New board
            </button>
          </div>
        </div>
      ) : null}

      {dialog === "new" ? (
        <NewBoardDialog onCreate={onCreate} onClose={() => setDialog(null)} />
      ) : null}
      {dialog === "settings" && active ? (
        <BoardSettingsDialog
          board={active}
          onSave={(title, description) => onUpdate(active.id, title, description)}
          onDelete={() => onDelete(active.id)}
          onClose={() => setDialog(null)}
        />
      ) : null}
    </div>
  );
};
