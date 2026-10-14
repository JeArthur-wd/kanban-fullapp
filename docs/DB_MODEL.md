# Database model (proposal)

This proposal is for the MVP and targets SQLite.

## Goals
- Support multiple users in the database.
- Enforce one board per user for the MVP.
- Keep ordering stable for columns and cards.

## Tables

### users
- Stores account records (future-ready).
- `username` is unique.

### boards
- One board per user (unique `user_id`).
- Title stored for future multi-board expansion.

### columns
- Ordered by `position` within a board.
- Renaming columns updates the `title`.

### cards
- Linked to columns, ordered by `position` within a column.
- `details` is a required text field (empty string allowed).
- `archived` is a soft-delete flag for future use.

## Ordering strategy
- `position` is an integer, starting at 0 and incremented by 1.
- Reordering updates affected `position` values within the parent scope.

## Migration approach
Not implemented yet: the schema has not changed since it was first created, and `init_db()` only runs `CREATE TABLE IF NOT EXISTS`. When the schema first needs to change:
- Use SQLite DDL migrations tracked by version.
- Store version in `PRAGMA user_version` and increment on migration.
- Keep migrations idempotent and forward-only.

Note: databases created before foreign keys were enforced have no `ON DELETE CASCADE` on their tables. Deleting a column still removes its cards explicitly in `board_ops.delete_column`, so behavior is the same.

## Connection settings
- `PRAGMA foreign_keys = ON` for every connection; `journal_mode = WAL` (set once in `init_db`); 10 second busy timeout.
- A user's board and its seed columns are created together, the first time the board is needed. Deleting every column leaves an empty board; it is not re-seeded.

## JSON schema reference
- See docs/kanban-schema.json
