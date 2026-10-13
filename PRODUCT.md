# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primary: the author's portfolio audience (employers, clients, reviewers) who open the deployed demo to judge craft. They sign in with the hardcoded demo account, move cards, and try the AI chat to see that it really works. The author also uses it as their own project board.

## Product Purpose
A single-board project management app: sign in, see a Kanban board with five renamable columns, drag cards between them, edit them, and ask an AI assistant in a sidebar to create, edit, move or delete cards. Success is a reviewer finishing a short session convinced that the app is real, polished and fast, and that the AI changes the board for real.

## Positioning
The AI assistant acts on the board directly (structured actions applied to persisted data), not just chat beside it.

## Operating Context
Used in a browser on desktop first; a reviewer may open it on a phone. Deployed as a single Docker container (FastAPI serving the static Next.js build, SQLite storage) on a cloud Docker host. AI calls go through OpenRouter; the current model is a free one, so replies can be slow (several seconds) or occasionally rate-limited.

## Capabilities and Constraints
- Hardcoded login `user` / `password`; one board per user; multi-user supported by the database but not exposed.
- Five fixed columns that can be renamed; cards have a title and details; add, edit, delete, drag and drop.
- AI chat sidebar with conversation history; AI actions: create, update, move, delete card.
- Scope of the customization: look and feel only. Features, behavior, data model and API stay as they are.
- Stack is fixed: Next.js 16, React 19, TypeScript, Tailwind v4, @dnd-kit. Existing tests (Vitest unit tests, Playwright e2e) must keep passing; controls are found by accessible name and test ids, so those must be preserved.
- Deployment target: cloud host that runs the existing Docker container (Render, Fly.io or Railway class), with persistent storage for SQLite. Not yet decided or set up.
- No emojis anywhere in the product.

## Brand Commitments
None binding. The name "Kanban Studio" and the current palette (yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, gray `#888888`) may both be replaced.

## Evidence on Hand
A working app with login, board, drag and drop, and a live AI sidebar. No logo, photography, testimonials or customer data exist; none may be invented.

## Product Principles
- The board is the product; the chrome around it stays quiet.
- Show that the AI really acts: changes it makes are visible and attributable.
- Every state is designed: loading, empty, error, slow AI reply, rate limit.
- A stranger should understand the app within seconds, with the login screen doing the explaining.
- Craft over feature count: no new features in this pass.

## Accessibility & Inclusion
Keep controls reachable by keyboard and named for screen readers (existing aria-labels stay). Maintain readable contrast and respect reduced motion.
