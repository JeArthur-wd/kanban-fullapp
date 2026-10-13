---
version: 1
slug: "frontend-src-app-page-tsx"
primary_target: "frontend/src/app/page.tsx"
related_targets: ["frontend/src/components/KanbanBoard.tsx","frontend/src/components/ChatSidebar.tsx"]
---

# Surface brief: Kanban Studio app (login, board, assistant)

Mode: Operate. Scope: every screen (login, loading, board, cards, forms, AI sidebar). Look and feel only; behavior and data unchanged.

Audience and job: portfolio reviewers and the author sign in with the demo account, move and edit cards, and use the AI sidebar to see that it really acts on the board. Quality bar: Linear, Trello, Notion, Asana/Height. Must stay scannable when the board fills.

## Direction contract
THESIS: The category standard played straight and executed at full craft: a calm light board, one blue accent, no costume. Refuses the old soft-SaaS template (blurred blobs, marketing header, tracked uppercase labels, giant radii).
OWN-WORLD: Cool-tinted light neutrals (ground #f6f7f9, column wells #eceef2, white cards), ink #172033, one blue (#1f5fe0) only for primary actions, focus and the user's own chat bubbles. Muted status dots per column are the only other colour. Geist for UI, tabular numerals for counts, 8px card radius, 1px borders plus a soft offset shadow, drawn SVG icons.
STORY: A visitor sees a real, fast, trustworthy tool within seconds; the assistant panel feels first-class, with a clear thinking state while a slow model replies.
FIRST VIEWPORT: Slim 56px top bar (name left, user and Log out right). Below: five column wells with title input, count badge and status dot, white cards with a muted delete button; assistant panel docked right at 300px (340px from 1536px), sticky, with message list, thinking indicator and composer.
FORM: Canon (category standard), chosen from the decision round; seed key 6d50d1c2.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
