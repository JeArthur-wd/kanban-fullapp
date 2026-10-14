import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";
import Home from "@/app/page";

type Reply = { status?: number; body?: unknown };
type Request = { body: unknown };
type Handler = (request: Request) => Reply | Promise<Reply>;

const board = (cards: Array<[string, string]>) => ({
    board: { id: "1", title: "My Board" },
    columns: [{ id: "1", title: "Backlog", position: 0, cardIds: cards.map(([id]) => id) }],
    cards: Object.fromEntries(
        cards.map(([id, title]) => [id, { id, title, details: "Details" }])
    ),
});

const emptyBoard = board([]);

// Routes fetch calls by "METHOD /path" and records each request body.
const installServer = (routes: Record<string, Handler>) => {
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

const signedOut: Record<string, Handler> = {
    "GET /api/session": () => ({ status: 401, body: { detail: "Not signed in" } }),
};
const signedIn: Record<string, Handler> = {
    "GET /api/session": () => ({ body: { username: "user" } }),
};

const signIn = async () => {
    await userEvent.type(await screen.findByPlaceholderText("user"), "user");
    await userEvent.type(screen.getByPlaceholderText("password"), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
};

afterEach(() => {
    vi.restoreAllMocks();
});

describe("Home page: sign in", () => {
    it("shows the login screen when there is no session", async () => {
        installServer(signedOut);
        render(<Home />);
        expect(await screen.findByText("Welcome back")).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });

    it("skips the login screen when the server session is still valid", async () => {
        installServer({ ...signedIn, "GET /api/board": () => ({ body: emptyBoard }) });
        render(<Home />);
        expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();
        expect(screen.queryByText("Welcome back")).not.toBeInTheDocument();
    });

    it("signs in through the server and loads the board", async () => {
        const server = installServer({
            ...signedOut,
            "POST /api/login": () => ({ body: { username: "user" } }),
            "GET /api/board": () => ({ body: emptyBoard }),
        });
        render(<Home />);
        await signIn();

        expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();
        expect(server.bodies("POST /api/login")).toEqual([
            { username: "user", password: "password" },
        ]);
    });

    it("shows an error for wrong credentials and stays on the login screen", async () => {
        installServer({
            ...signedOut,
            "POST /api/login": () => ({ status: 401, body: { detail: "Incorrect username or password." } }),
        });
        render(<Home />);
        await signIn();

        expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect username or password.");
        expect(screen.getByText("Welcome back")).toBeInTheDocument();
    });

    it("shows the server message when sign-in is rate limited", async () => {
        installServer({
            ...signedOut,
            "POST /api/login": () => ({ status: 429, body: { detail: "Too many sign-in attempts." } }),
        });
        render(<Home />);
        await signIn();
        expect(await screen.findByRole("alert")).toHaveTextContent("Too many sign-in attempts.");
    });

    it("logs out through the server", async () => {
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "POST /api/logout": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        await userEvent.click(await screen.findByRole("button", { name: /log out/i }));

        expect(await screen.findByText("Welcome back")).toBeInTheDocument();
        expect(server.count("POST /api/logout")).toBe(1);
    });

    it("returns to the login screen when the session ends mid-use", async () => {
        installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: board([["9", "Card"]]) }),
            "DELETE /api/cards/9": () => ({ status: 401, body: { detail: "Not signed in" } }),
        });
        render(<Home />);
        await userEvent.click(await screen.findByRole("button", { name: /delete card/i }));

        expect(await screen.findByText("Welcome back")).toBeInTheDocument();
        expect(screen.getByRole("alert")).toHaveTextContent("Your session has ended");
    });
});

describe("Home page: board loading", () => {
    it("shows the error and a retry button when the first load fails", async () => {
        let attempts = 0;
        installServer({
            ...signedIn,
            "GET /api/board": () => {
                attempts += 1;
                return attempts === 1
                    ? { status: 500, body: { detail: "boom" } }
                    : { body: board([["9", "Loaded after retry"]]) };
            },
        });
        render(<Home />);

        expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load the board");
        expect(screen.queryByText("Loading your board")).not.toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /try again/i }));
        expect(await screen.findByText("Loaded after retry")).toBeInTheDocument();
    });

    it("ignores a slow, older board response that arrives after a newer one", async () => {
        let loads = 0;
        let releaseStale: (reply: Reply) => void = () => {};
        const stale = new Promise<Reply>((resolve) => {
            releaseStale = resolve;
        });
        installServer({
            ...signedIn,
            "GET /api/board": () => {
                loads += 1;
                if (loads === 1) return { body: board([["1", "First"], ["2", "Second"]]) };
                if (loads === 2) return stale;
                return { body: board([]) };
            },
            "DELETE /api/cards/1": () => ({ body: { status: "ok" } }),
            "DELETE /api/cards/2": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);

        await userEvent.click(await screen.findByRole("button", { name: /delete first/i }));
        await userEvent.click(await screen.findByRole("button", { name: /delete second/i }));
        await waitFor(() => expect(loads).toBe(3));
        await waitFor(() => expect(screen.queryByText("Second")).not.toBeInTheDocument());

        await act(async () => {
            releaseStale({ body: board([["2", "Second"]]) });
        });

        expect(screen.queryByText("Second")).not.toBeInTheDocument();
    });
});

describe("Home page: board errors are shown", () => {
    it("tells the user when a card cannot be deleted, and restores it", async () => {
        installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: board([["9", "Keep me"]]) }),
            "DELETE /api/cards/9": () => ({ status: 500, body: { detail: "boom" } }),
        });
        render(<Home />);
        await userEvent.click(await screen.findByRole("button", { name: /delete keep me/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Unable to remove the card.");
        expect(await screen.findByText("Keep me")).toBeInTheDocument();
    });

    it("tells the user when a column rename is rejected, and restores the title", async () => {
        installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "PATCH /api/columns/1": () => ({ status: 422, body: { detail: [] } }),
        });
        render(<Home />);
        const input = await screen.findByLabelText("Column title");
        await userEvent.clear(input);
        await userEvent.type(input, "Renamed");
        await userEvent.tab();

        expect(await screen.findByRole("alert")).toHaveTextContent("Unable to save column changes.");
        await waitFor(() => expect(screen.getByLabelText("Column title")).toHaveValue("Backlog"));
    });

    it("tells the user when a card cannot be added", async () => {
        installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "POST /api/cards": () => ({ status: 500, body: { detail: "boom" } }),
        });
        render(<Home />);
        await userEvent.click(await screen.findByRole("button", { name: /add a card/i }));
        await userEvent.type(screen.getByPlaceholderText(/card title/i), "New one");
        await userEvent.click(screen.getByRole("button", { name: /^add card$/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Unable to add the card.");
    });
});

describe("Home page: column titles", () => {
    it("saves a renamed column once, on blur, not on every keystroke", async () => {
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "PATCH /api/columns/1": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        const input = await screen.findByLabelText("Column title");
        await userEvent.clear(input);
        await userEvent.type(input, "Ideas");
        expect(server.count("PATCH /api/columns/1")).toBe(0);

        await userEvent.tab();
        await waitFor(() => expect(server.count("PATCH /api/columns/1")).toBe(1));
        expect(server.bodies("PATCH /api/columns/1")).toEqual([{ title: "Ideas" }]);
    });

    it("saves on Enter", async () => {
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "PATCH /api/columns/1": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        const input = await screen.findByLabelText("Column title");
        await userEvent.clear(input);
        await userEvent.type(input, "Plan{Enter}");
        await waitFor(() => expect(server.count("PATCH /api/columns/1")).toBe(1));
    });

    it("never sends an empty title and puts the old one back", async () => {
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "PATCH /api/columns/1": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        const input = await screen.findByLabelText("Column title");
        await userEvent.clear(input);
        await userEvent.tab();

        expect(server.count("PATCH /api/columns/1")).toBe(0);
        expect(screen.getByLabelText("Column title")).toHaveValue("Backlog");
    });

    it("Escape cancels an edit", async () => {
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
        });
        render(<Home />);
        const input = await screen.findByLabelText("Column title");
        await userEvent.type(input, " extra{Escape}");

        expect(server.count("PATCH /api/columns/1")).toBe(0);
        expect(screen.getByLabelText("Column title")).toHaveValue("Backlog");
    });
});

describe("Home page: chat", () => {
    const openChat = async () => {
        render(<Home />);
        return screen.findByLabelText("Chat message");
    };

    it("applies chat updates to the board", async () => {
        installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "POST /api/chat": () => ({
                body: {
                    response: "Created a card.",
                    actions: [{ type: "create_card" }],
                    board: board([["9", "AI created"]]),
                },
            }),
        });
        await userEvent.type(await openChat(), "Add a card");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));

        expect(await screen.findByText("AI created")).toBeInTheDocument();
        expect(screen.getByText("Created a card.")).toBeInTheDocument();
    });

    it("shows the server's explanation when the assistant fails", async () => {
        installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "POST /api/chat": () => ({
                status: 429,
                body: { detail: "The AI service is busy right now. Please try again in a moment." },
            }),
        });
        await userEvent.type(await openChat(), "hello");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));

        const alerts = await screen.findAllByRole("alert");
        expect(alerts.some((alert) => /busy right now/.test(alert.textContent ?? ""))).toBe(true);
    });

    it("does not send the failure notice back to the model as history", async () => {
        let call = 0;
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "POST /api/chat": () => {
                call += 1;
                return call === 1
                    ? { status: 502, body: { detail: "OpenRouter returned an error" } }
                    : { body: { response: "Fine.", actions: [], board: emptyBoard } };
            },
        });
        const input = await openChat();
        await userEvent.type(input, "first");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));
        await screen.findByText("Something went wrong. Please try again.");

        await userEvent.type(input, "second");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));
        await screen.findByText("Fine.");

        const bodies = server.bodies("POST /api/chat") as Array<{ history: unknown[] }>;
        expect(bodies[1].history).toEqual([{ role: "user", content: "first" }]);
    });

    it("sends at most 20 past messages", async () => {
        const server = installServer({
            ...signedIn,
            "GET /api/board": () => ({ body: emptyBoard }),
            "POST /api/chat": () => ({ body: { response: "ok", actions: [], board: emptyBoard } }),
        });
        const input = await openChat();
        for (let index = 0; index < 13; index += 1) {
            await userEvent.type(input, `m${index}`);
            await userEvent.click(screen.getByRole("button", { name: /send/i }));
            await waitFor(() => expect(within(document.body).getAllByText("ok")).toHaveLength(index + 1));
        }
        const bodies = server.bodies("POST /api/chat") as Array<{ history: unknown[] }>;
        expect(bodies[12].history).toHaveLength(20);
    }, 60000);
});
