# Frontend overview

## Stack
- Next.js 16 App Router
- React 19
- TypeScript
- Tailwind CSS v4 (via @tailwindcss/postcss)
- Drag-and-drop via @dnd-kit
- Unit testing with Vitest and Testing Library
- E2E testing with Playwright

## Entry points 
- App shell: src/app/layout.tsx
- Home route: src/app/page.tsx (renders the Kanban board)
- Global styles: src/app/globals.css

## UI components
- KanbanBoard: src/components/KanbanBoard.tsx
  - Owns board state (initialData from lib/kanban)
  - Handles drag-and-drop, column rename, add/delete cards
  - Uses DndContext + DragOverlay
- KanbanColumn: src/components/KanbanColumn.tsx
  - Droppable column surface
  - Renders column header, cards list, and NewCardForm
- KanbanCard: src/components/KanbanCard.tsx
  - Sortable card
  - Displays title/details and a remove button
- KanbanCardPreview: src/components/KanbanCardPreview.tsx
  - Visual preview used in drag overlay
- NewCardForm: src/components/NewCardForm.tsx
  - Inline form to add cards (title required, details optional)

## Data model and utilities
- Kanban data types and helpers: src/lib/kanban.ts
  - Types: Card, Column, BoardData
  - initialData: demo board content
  - moveCard: reorders/moves cards across columns
  - createId: generates random IDs for cards

## Tests
- Prefer meaningful unit coverage, with a practical target around 80% where it adds real value; do not add weak or redundant tests solely to reach a percentage.
- Unit tests
  - src/components/KanbanBoard.test.tsx
  - src/lib/kanban.test.ts
- Robust integration testing should exercise real user flows, including login, board rendering, drag-and-drop, card editing, and refresh persistence across the backend-served app.
- Test setup: src/test/setup.ts
- E2E tests: tests/kanban.spec.ts

## Build and scripts
- Scripts: package.json
  - dev, build, start, lint
  - test:unit, test:e2e, test:all

## Notes
- The current frontend is a standalone demo that uses in-memory state only.
- Styling uses CSS variables defined in globals.css to match the shared color scheme.
