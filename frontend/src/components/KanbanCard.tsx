import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import { CloseIcon } from "@/components/icons";

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
        "cursor-grab rounded-lg border border-line bg-surface p-3 shadow-card transition-[border-color,box-shadow] duration-150",
        "hover:border-line-strong active:cursor-grabbing",
        isDragging && "border-dashed border-line-strong bg-well/60 opacity-50 shadow-none"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="break-words text-sm font-medium leading-5 text-ink">
            {card.title}
          </h4>
          <p className="mt-1 line-clamp-4 break-words text-[13px] leading-5 text-muted">
            {card.details}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="-mr-1 -mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md text-muted transition-colors hover:bg-danger-soft hover:text-danger"
          aria-label={`Delete ${card.title}`}
          title="Delete card"
        >
          <CloseIcon width={14} height={14} />
        </button>
      </div>
    </article>
  );
};
