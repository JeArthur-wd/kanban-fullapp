import type { ReactNode } from "react";
import { BoardMark, LogOutIcon, UserIcon } from "@/components/icons";

type AppHeaderProps = {
  // The board switcher, when the user has boards.
  boardControls?: ReactNode;
  accountLabel?: string;
  onOpenAccount?: () => void;
  onLogout?: () => void;
};

export const AppHeader = ({ boardControls, accountLabel, onOpenAccount, onLogout }: AppHeaderProps) => (
  <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-line bg-surface px-4 sm:gap-3 sm:px-6">
    <BoardMark />
    <h1 className="hidden text-[15px] font-semibold tracking-tight text-ink sm:block">
      Kanban Studio
    </h1>
    {boardControls ? (
      <>
        <span className="hidden h-5 w-px bg-line sm:block" aria-hidden />
        {boardControls}
      </>
    ) : null}
    <div className="flex-1" />
    {onOpenAccount ? (
      <button
        type="button"
        onClick={onOpenAccount}
        className="flex h-8 min-w-0 items-center gap-1.5 rounded-md px-2 text-[13px] font-medium text-ink transition-colors hover:bg-well"
        aria-label="Account settings"
        title="Account settings"
      >
        <UserIcon width={15} height={15} className="shrink-0 text-muted" />
        <span className="hidden max-w-40 truncate sm:inline">{accountLabel}</span>
      </button>
    ) : null}
    {onLogout ? (
      <button
        type="button"
        onClick={onLogout}
        className="flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-line px-3 text-[13px] font-medium text-ink transition-colors hover:border-line-strong hover:bg-ground"
      >
        <LogOutIcon width={14} height={14} />
        Log out
      </button>
    ) : null}
  </header>
);
