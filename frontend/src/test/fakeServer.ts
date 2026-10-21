// A fake API for page tests: routes fetch calls by "METHOD /path" and records each body.
import { vi } from "vitest";

export type Reply = { status?: number; body?: unknown };
type Request = { body: unknown };
export type Handler = (request: Request) => Reply | Promise<Reply>;

export const board = (cards: Array<[string, string]>) => ({
    board: { id: "1", title: "My Board" },
    columns: [{ id: "1", title: "Backlog", position: 0, cardIds: cards.map(([id]) => id) }],
    cards: Object.fromEntries(
        cards.map(([id, title]) => [id, { id, title, details: "Details" }])
    ),
});

export const emptyBoard = board([]);

export const summary = (id: string, title: string, cardCount = 0) => ({
    id,
    title,
    description: "",
    columnCount: 1,
    cardCount,
});

export const oneBoard = () => ({ body: [summary("1", "My Board")] });

// Routes fetch calls by "METHOD /path" and records each request body.
export const installServer = (routes: Record<string, Handler>) => {
    const calls: Array<{ key: string; body: unknown }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
        const method = (init?.method ?? "GET").toUpperCase();
        const key = `${method} ${String(input)}`;
        const body = init?.body ? JSON.parse(String(init.body)) : undefined;
        calls.push({ key, body });
        const handler = routes[key];
        const reply = handler ? await handler({ body }) : { status: 404, body: { detail: "No route" } };
        const status = reply.status ?? 200;
        return {
            ok: status < 400,
            status,
            json: async () => reply.body,
            text: async () => JSON.stringify(reply.body ?? ""),
        } as Response;
    });
    return {
        calls,
        count: (key: string) => calls.filter((call) => call.key === key).length,
        bodies: (key: string) => calls.filter((call) => call.key === key).map((call) => call.body),
    };
};

export const signedOut: Record<string, Handler> = {
    "GET /api/session": () => ({ status: 401, body: { detail: "Not signed in" } }),
    "GET /api/boards": oneBoard,
};
export const signedIn: Record<string, Handler> = {
    "GET /api/session": () => ({ body: { id: "1", username: "user", displayName: "" } }),
    "GET /api/boards": oneBoard,
};
