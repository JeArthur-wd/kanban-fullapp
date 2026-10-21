# Frontend overview

## Stack
- Next.js 16 App Router, statically exported (`npm run build` writes `out/`, which the backend serves)
- React 19, TypeScript, Tailwind CSS v4 (via @tailwindcss/postcss)
- Drag-and-drop via @dnd-kit (pointer and keyboard)
- Unit tests: Vitest and Testing Library (jsdom). E2E: Playwright against the backend-served app.

## Entry points
- App shell: src/app/layout.tsx
- Home route: src/app/page.tsx
- Global styles and design tokens: src/app/globals.css (see DESIGN.md)

## Page flow (src/app/page.tsx)
- Checks `GET /api/session`; without a session shows `AuthScreen` (sign in or create an account).
- Loads the board list, opens the board used last (localStorage `kanban:lastBoard`) or the first one, and shows an empty state with "Create a board" when there are none.
- Owns all API calls for board changes: optimistic updates, then a background refresh; errors put the board back in sync and show a toast. Stale board responses are dropped (`refreshSeq`).
- The chat belongs to the open board and starts empty when another board is opened.

## Components (src/components)
- AppHeader: brand, board controls, account button, log out.
- BoardSwitcher: board menu (switch, new board) and the board settings button. BoardDialogs: NewBoardDialog (name, description, basic or sample template) and BoardSettingsDialog (rename, describe, delete with confirmation).
- AccountDialog: display name, password change (other devices are signed out), delete account (password required).
- AuthScreen: sign-in and sign-up forms.
- KanbanBoard: drag-and-drop for the open board (DndContext + DragOverlay); renders KanbanColumn per column and the sidebar.
- KanbanColumn: droppable column, title edited in place (saved on blur or Enter, Escape cancels), cards, NewCardForm.
- KanbanCard: sortable card with delete button. KanbanCardPreview: drag overlay.
- ChatSidebar: AI chat for the open board.
- Dialog: modal shell (Escape and backdrop close, focus in and back). useDismiss: closes menus on Escape or an outside press. ui.ts: shared class names. icons.tsx: drawn SVG icons.

## Data and API
- src/lib/api.ts: fetch wrapper (30s timeout, `ApiError` with the server's `detail`, any 401 returns to sign-in) and one function per endpoint.
- src/lib/kanban.ts: types (Card with priority and due date, Column, BoardData), id prefixing (`col-`, `card-`), `moveCard`.

## Tests
- Aim for meaningful coverage (around 80% where it adds value); do not add weak tests to reach a number.
- Unit: src/**/*.test.tsx. Page tests use the fake API in src/test/fakeServer.ts (`installServer` routes "METHOD /path").
- E2E: tests/*.spec.ts. `auth.setup.ts` signs in once and the suite reuses the cookie; `accounts.spec.ts` signs up throwaway accounts and deletes them. Fixtures are prefixed `E2E ` and removed after each test.
