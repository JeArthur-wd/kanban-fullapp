import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="cursor-grabbing rounded-lg border border-line-strong bg-surface p-3 shadow-lift ring-1 ring-accent/20">
    <h4 className="break-words text-sm font-medium leading-5 text-ink">
      {card.title}
    </h4>
    <p className="mt-1 line-clamp-4 break-words text-[13px] leading-5 text-muted">
      {card.details}
    </p>
  </article>
);
