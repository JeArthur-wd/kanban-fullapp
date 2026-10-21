// Class names shared by forms and dialogs, following DESIGN.md.
export const labelClass = "text-[13px] font-medium text-ink";

export const inputClass =
  "mt-1.5 h-9 w-full rounded-md border border-line bg-surface px-2.5 text-sm text-ink transition-colors hover:border-line-strong focus:border-accent";

export const primaryButton =
  "h-8 rounded-md bg-accent px-3 text-[13px] font-medium text-white transition-colors hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50";

export const outlineButton =
  "h-8 rounded-md border border-line bg-surface px-3 text-[13px] font-medium text-ink transition-colors hover:border-line-strong hover:bg-ground disabled:cursor-not-allowed disabled:opacity-50";

export const ghostButton =
  "h-8 rounded-md px-3 text-[13px] font-medium text-muted transition-colors hover:bg-well hover:text-ink";

export const dangerButton =
  "h-8 rounded-md bg-danger px-3 text-[13px] font-medium text-white transition-colors hover:bg-danger/90 disabled:cursor-not-allowed disabled:opacity-50";

export const errorText = "text-[13px] font-medium text-danger";

export const errorMessage = (err: unknown, fallback: string) =>
  err instanceof Error && "detail" in err && typeof err.detail === "string" && err.detail
    ? err.detail
    : fallback;
