"use client";

import { useMemo, useRef, useState, type ReactNode } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  pointerWithin,
  rectIntersection,
  MeasuringStrategy,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData, type Column } from "@/lib/kanban";

type KanbanBoardProps = {
  board: BoardData;
  onBoardChange: React.Dispatch<React.SetStateAction<BoardData>>;
  onRenameColumn?: (columnId: string, title: string) => void;
  onAddCard?: (columnId: string, title: string, details: string) => void;
  onDeleteCard?: (columnId: string, cardId: string) => void;
  onMoveCard?: (activeId: string, nextColumns: Column[]) => void;
  sidebar?: ReactNode;
};

export const KanbanBoard = ({
  board,
  onBoardChange,
  onRenameColumn,
  onAddCard,
  onDeleteCard,
  onMoveCard,
  sidebar,
}: KanbanBoardProps) => {
  const setBoard = onBoardChange;
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const lastOverId = useRef<string | null>(null);

  const collisionDetection: CollisionDetection = useMemo(
    () => (args) => {
      const filtered = {
        ...args,
        droppableContainers: args.droppableContainers.filter(
          (container) => container.id !== args.active.id
        ),
      };
      const pointerCollisions = pointerWithin(filtered);
      if (pointerCollisions.length > 0) {
        return pointerCollisions;
      }
      const intersections = rectIntersection(filtered);
      if (intersections.length > 0) {
        return intersections;
      }
      return closestCorners(filtered);
    },
    []
  );

  const handleDragStart = (event: DragStartEvent) => {
    const activeId = event.active.data.current?.cardId as string | undefined;
    if (!activeId) {
      return;
    }
    setActiveCardId(activeId);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    const activeId = active.data.current?.cardId as string | undefined;
    const activeColumnId = active.data.current?.columnId as string | undefined;
    const overIdFromData = over?.data.current?.cardId as string | undefined;
    const overColumnFromData = over?.data.current?.columnId as string | undefined;
    const isCrossColumn =
      activeColumnId && overColumnFromData && activeColumnId !== overColumnFromData;
    const resolvedOverId =
      (overIdFromData && overIdFromData !== activeId && !isCrossColumn
        ? overIdFromData
        : undefined) ??
      overColumnFromData ??
      lastOverId.current;
    if (!activeId || !resolvedOverId || activeId === resolvedOverId) {
      lastOverId.current = null;
      return;
    }

    lastOverId.current = null;

    // Work out the new order from the current props, outside the state updater, so the
    // updater stays pure and the server is told once per drop.
    const nextColumns = moveCard(board.columns, activeId, resolvedOverId);
    if (nextColumns === board.columns) {
      return;
    }
    setBoard((prev) => ({ ...prev, columns: nextColumns }));
    onMoveCard?.(activeId, nextColumns);
  };

  const handleDragOver = (event: { active: DragEndEvent["active"]; over: DragEndEvent["over"] }) => {
    if (event.over) {
      const activeColumnId = event.active.data.current?.columnId as string | undefined;
      const overCardId = event.over.data.current?.cardId as string | undefined;
      const overColumnId = event.over.data.current?.columnId as string | undefined;
      if (activeColumnId && overColumnId && activeColumnId !== overColumnId) {
        lastOverId.current = overColumnId;
        return;
      }
      lastOverId.current = overCardId ?? overColumnId ?? null;
    }
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
    onRenameColumn?.(columnId, title);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (onAddCard) {
      onAddCard(columnId, title, details);
      return;
    }
    const id = createId("card");
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setBoard((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
            : column
        ),
      };
    });
    onDeleteCard?.(columnId, cardId);
  };

  const activeCard = activeCardId ? board.cards[activeCardId] : null;

  return (
    <main
      className={
        sidebar
          ? "grid flex-1 grid-cols-[minmax(0,1fr)] gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_300px] 2xl:grid-cols-[minmax(0,1fr)_340px] 2xl:p-6"
          : "flex-1 p-4 sm:p-6"
      }
    >
      <DndContext
        sensors={sensors}
        measuring={{ droppable: { strategy: MeasuringStrategy.Always } }}
        collisionDetection={collisionDetection}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <section className="relative grid min-w-0 auto-cols-[minmax(16rem,1fr)] grid-flow-col gap-3 xl:auto-cols-[minmax(10.5rem,1fr)] overflow-x-auto pb-2 lg:min-h-[calc(100dvh-6rem)]">
          {board.columns.map((column, index) => (
            <KanbanColumn
              key={column.id}
              column={column}
              cards={column.cardIds.map((cardId) => board.cards[cardId])}
              index={index}
              onRename={handleRenameColumn}
              onAddCard={handleAddCard}
              onDeleteCard={handleDeleteCard}
            />
          ))}
        </section>
        <DragOverlay>
          {activeCard ? (
            <div className="w-[272px]">
              <KanbanCardPreview card={activeCard} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
      {sidebar ? (
        <div className="lg:sticky lg:top-[4.5rem] lg:self-start">{sidebar}</div>
      ) : null}
    </main>
  );
};
