import clsx from "clsx";
import { useDndContext, useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

const STATUS_DOTS = [
  "var(--dot-backlog)",
  "var(--dot-discovery)",
  "var(--dot-progress)",
  "var(--dot-review)",
  "var(--dot-done)",
];

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  index: number;
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  index,
  onRename,
  onAddCard,
  onDeleteCard,
}: KanbanColumnProps) => {
  const { over } = useDndContext();
  const { setNodeRef, isOver } = useDroppable({
    id: `column-${column.id}`,
    data: { columnId: column.id },
  });
  const overColumnId = over?.data?.current?.columnId as string | undefined;
  const isColumnOver = isOver || overColumnId === column.id;

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-w-0 flex-col rounded-xl bg-well p-2 transition-shadow duration-150",
        isColumnOver && "shadow-[inset_0_0_0_2px_var(--accent)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-center gap-2 px-1.5 pb-2 pt-1">
        <span
          className="h-2 w-2 shrink-0 rounded-full"
          style={{ background: STATUS_DOTS[index % STATUS_DOTS.length] }}
          aria-hidden
        />
        <input
          value={column.title}
          onChange={(event) => onRename(column.id, event.target.value)}
          className="-mx-1 min-w-0 flex-1 rounded-md bg-transparent px-1 py-0.5 text-sm font-semibold text-ink transition-colors hover:bg-surface/70 focus:bg-surface"
          aria-label="Column title"
        />
        <span className="tabular rounded-full bg-surface/80 px-2 py-0.5 text-xs font-medium text-muted">
          {cards.length}
          <span className="sr-only"> cards</span>
        </span>
      </div>
      <div className="flex flex-col gap-2">
        <SortableContext
          id={column.id}
          items={column.cardIds.map((cardId) => `card-${cardId}`)}
          strategy={verticalListSortingStrategy}
        >
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              columnId={column.id}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex min-h-24 items-center justify-center rounded-lg border border-dashed border-line-strong px-3 py-6 text-center text-[13px] text-muted">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
