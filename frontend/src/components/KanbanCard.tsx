import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  columnId: string;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({ card, columnId, onDelete }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({
      id: `card-${card.id}`,
      data: { cardId: card.id, columnId },
    });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
            {card.details}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-transparent text-base leading-none text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
          aria-label={`Delete ${card.title}`}
          title="Delete card"
        >
          &times;
        </button>
      </div>
    </article>
  );
};
