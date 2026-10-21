# Database model

SQLite, raw `sqlite3`. Schema version 2 (see `docs/kanban-schema.json`).

## Goals
- Many users, each with any number of boards.
- Keep ordering stable for columns and cards.

## Tables

### users
- `username` is unique and stored lower-case. `password_hash` is scrypt; `display_name` is optional.
- `session_epoch` is copied into the session cookie; bumping it (password change) ends other sessions.
- `id` is AUTOINCREMENT so a deleted user's id, which an old cookie may name, is never reused.

### boards
- Any number per user, with a title and description. Deleting a user deletes its boards.

### columns
- Ordered by `position` within a board.
- Renaming columns updates the `title`.

### cards
- Linked to columns, ordered by `position` within a column.
- `details` is a required text field (empty string allowed).
- `priority` is one of none, low, medium, high (a CHECK constraint); `due_date` is an ISO date or NULL.
- `archived` is a soft-delete flag; archived cards are left out of the board payload and counts.

## Ordering strategy
- `position` is an integer, starting at 0 and incremented by 1.
- Reordering updates affected `position` values within the parent scope.

## Migrations
`database.MIGRATIONS` is an ordered list of functions; `PRAGMA user_version` records how many have run. `init_db()` runs the missing ones at startup, each in one transaction with foreign keys off, and refuses a migration that adds broken references (orphans already present are tolerated). To change the schema, append a function; never edit one that has shipped.

1. The MVP schema (`CREATE TABLE IF NOT EXISTS`, so MVP databases pass through unchanged).
2. Rebuilds all four tables: drops `UNIQUE(user_id)` on boards, adds the account fields, board description, card priority and due date, AUTOINCREMENT user ids and `ON DELETE CASCADE` everywhere. Rows whose parent is missing are not copied.

## Connection settings
- `PRAGMA foreign_keys = ON` for every connection; `journal_mode = WAL` (set once in `init_db`); 10 second busy timeout.
- A new account gets one board with the sample content (`config.INITIAL_COLUMNS`); boards created later use the basic columns or the sample. Deleting every column, or every board, leaves it empty; nothing is re-seeded.

## JSON schema reference
- See docs/kanban-schema.json
