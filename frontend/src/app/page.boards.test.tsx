import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";
import Home from "@/app/page";
import {
    board,
    emptyBoard,
    installServer,
    signedIn,
    signedOut,
    summary,
    type Handler,
} from "@/test/fakeServer";

afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
});

const namedBoard = (id: string, title: string, cards: Array<[string, string]> = []) => ({
    ...board(cards),
    board: { id, title, description: "" },
});

const twoBoards: Record<string, Handler> = {
    ...signedIn,
    "GET /api/boards": () => ({ body: [summary("1", "Roadmap", 1), summary("2", "Hiring", 1)] }),
    "GET /api/boards/1": () => ({ body: namedBoard("1", "Roadmap", [["11", "Roadmap card"]]) }),
    "GET /api/boards/2": () => ({ body: namedBoard("2", "Hiring", [["21", "Hiring card"]]) }),
};

const openSwitcher = async () => {
    await userEvent.click(await screen.findByRole("button", { name: /switch board/i }));
    return screen.getByRole("menu", { name: "Boards" });
};

describe("Sign up", () => {
    const openSignUp = async () => {
        await userEvent.click(await screen.findByRole("button", { name: /create an account/i }));
        expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument();
    };

    it("creates an account, signs in and opens its first board", async () => {
        const server = installServer({
            ...signedOut,
            "POST /api/register": () => ({
                body: { id: "5", username: "ada", displayName: "Ada" },
            }),
            "GET /api/boards/1": () => ({ body: namedBoard("1", "My Board", [["1", "Sample card"]]) }),
        });
        render(<Home />);
        await openSignUp();
        await userEvent.type(screen.getByLabelText("Username"), "ada");
        await userEvent.type(screen.getByLabelText(/^Name/), "Ada");
        await userEvent.type(screen.getByLabelText("Password"), "long-enough");
        await userEvent.type(screen.getByLabelText("Confirm password"), "long-enough");
        await userEvent.click(screen.getByRole("button", { name: "Create account" }));

        expect(await screen.findByText("Sample card")).toBeInTheDocument();
        expect(server.bodies("POST /api/register")).toEqual([
            { username: "ada", password: "long-enough", display_name: "Ada" },
        ]);
        expect(screen.getByRole("button", { name: "Account settings" })).toHaveTextContent("Ada");
    });

    it("checks that the passwords match before sending anything", async () => {
        const server = installServer(signedOut);
        render(<Home />);
        await openSignUp();
        await userEvent.type(screen.getByLabelText("Username"), "ada");
        await userEvent.type(screen.getByLabelText("Password"), "long-enough");
        await userEvent.type(screen.getByLabelText("Confirm password"), "different!");
        await userEvent.click(screen.getByRole("button", { name: "Create account" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("The passwords do not match.");
        expect(server.count("POST /api/register")).toBe(0);
    });

    it("shows the server's reason when the username is taken", async () => {
        installServer({
            ...signedOut,
            "POST /api/register": () => ({ status: 409, body: { detail: "That username is taken." } }),
        });
        render(<Home />);
        await openSignUp();
        await userEvent.type(screen.getByLabelText("Username"), "user");
        await userEvent.type(screen.getByLabelText("Password"), "long-enough");
        await userEvent.type(screen.getByLabelText("Confirm password"), "long-enough");
        await userEvent.click(screen.getByRole("button", { name: "Create account" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("That username is taken.");
    });

    it("can go back to the sign-in form", async () => {
        installServer(signedOut);
        render(<Home />);
        await openSignUp();
        await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
        expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    });
});

describe("Boards", () => {
    it("opens the board used last time", async () => {
        window.localStorage.setItem("kanban:lastBoard", "2");
        const server = installServer(twoBoards);
        render(<Home />);
        expect(await screen.findByText("Hiring card")).toBeInTheDocument();
        expect(server.count("GET /api/boards/1")).toBe(0);
    });

    it("falls back to the first board when the remembered one is gone", async () => {
        window.localStorage.setItem("kanban:lastBoard", "99");
        installServer(twoBoards);
        render(<Home />);
        expect(await screen.findByText("Roadmap card")).toBeInTheDocument();
    });

    it("switches boards from the header and remembers the choice", async () => {
        installServer(twoBoards);
        render(<Home />);
        await screen.findByText("Roadmap card");

        const menu = await openSwitcher();
        expect(within(menu).getByRole("menuitemradio", { name: /roadmap/i })).toHaveAttribute(
            "aria-checked",
            "true"
        );
        await userEvent.click(within(menu).getByRole("menuitemradio", { name: /hiring/i }));

        expect(await screen.findByText("Hiring card")).toBeInTheDocument();
        expect(screen.queryByText("Roadmap card")).not.toBeInTheDocument();
        expect(window.localStorage.getItem("kanban:lastBoard")).toBe("2");
    });

    it("closes the board menu with Escape", async () => {
        installServer(twoBoards);
        render(<Home />);
        await screen.findByText("Roadmap card");
        await openSwitcher();
        await userEvent.keyboard("{Escape}");
        expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    });

    it("starts a fresh chat for each board and sends it to that board", async () => {
        const server = installServer({
            ...twoBoards,
            "POST /api/boards/1/chat": () => ({
                body: { response: "Roadmap reply", actions: [], board: namedBoard("1", "Roadmap") },
            }),
            "POST /api/boards/2/chat": () => ({
                body: { response: "Hiring reply", actions: [], board: namedBoard("2", "Hiring") },
            }),
        });
        render(<Home />);
        await screen.findByText("Roadmap card");
        await userEvent.type(screen.getByLabelText("Chat message"), "hello");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));
        expect(await screen.findByText("Roadmap reply")).toBeInTheDocument();

        await userEvent.click(within(await openSwitcher()).getByRole("menuitemradio", { name: /hiring/i }));
        await screen.findByText("Hiring card");
        expect(screen.queryByText("Roadmap reply")).not.toBeInTheDocument();

        await userEvent.type(screen.getByLabelText("Chat message"), "hi");
        await userEvent.click(screen.getByRole("button", { name: /send/i }));
        expect(await screen.findByText("Hiring reply")).toBeInTheDocument();
        expect(server.bodies("POST /api/boards/2/chat")).toEqual([
            { message: "hi", history: [], apply_updates: true },
        ]);
    });

    it("creates a board from the menu and opens it", async () => {
        let boards = [summary("1", "Roadmap")];
        const server = installServer({
            ...twoBoards,
            "GET /api/boards": () => ({ body: boards }),
            "POST /api/boards": () => {
                boards = [...boards, summary("3", "Launch")];
                return { body: { id: "3" } };
            },
            "GET /api/boards/3": () => ({ body: namedBoard("3", "Launch", [["31", "Launch card"]]) }),
        });
        render(<Home />);
        await screen.findByText("Roadmap card");

        await userEvent.click(within(await openSwitcher()).getByRole("menuitem", { name: /new board/i }));
        const dialog = screen.getByRole("dialog", { name: "New board" });
        await userEvent.type(within(dialog).getByLabelText("Name"), "Launch");
        await userEvent.click(within(dialog).getByLabelText(/sample board/i));
        await userEvent.click(within(dialog).getByRole("button", { name: "Create board" }));

        expect(await screen.findByText("Launch card")).toBeInTheDocument();
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
        expect(server.bodies("POST /api/boards")).toEqual([
            { title: "Launch", description: "", template: "sample" },
        ]);
        expect(screen.getByRole("button", { name: /switch board/i })).toHaveTextContent("Launch");
    });

    it("needs a name before creating a board", async () => {
        const server = installServer(twoBoards);
        render(<Home />);
        await screen.findByText("Roadmap card");
        await userEvent.click(within(await openSwitcher()).getByRole("menuitem", { name: /new board/i }));
        await userEvent.click(screen.getByRole("button", { name: "Create board" }));

        expect(screen.getByRole("alert")).toHaveTextContent("Give the board a name.");
        expect(server.count("POST /api/boards")).toBe(0);
    });

    it("renames a board in its settings", async () => {
        const server = installServer({
            ...twoBoards,
            "PATCH /api/boards/1": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        await screen.findByText("Roadmap card");

        await userEvent.click(screen.getByRole("button", { name: "Board settings" }));
        const dialog = screen.getByRole("dialog", { name: "Board settings" });
        const name = within(dialog).getByLabelText("Name");
        await userEvent.clear(name);
        await userEvent.type(name, "Product roadmap");
        await userEvent.type(within(dialog).getByLabelText("Description"), "Next two quarters");
        await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));

        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
        expect(server.bodies("PATCH /api/boards/1")).toEqual([
            { title: "Product roadmap", description: "Next two quarters" },
        ]);
        expect(screen.getByRole("button", { name: /switch board/i })).toHaveTextContent(
            "Product roadmap"
        );
    });

    it("shows why a board could not be saved and keeps the dialog open", async () => {
        installServer({
            ...twoBoards,
            "PATCH /api/boards/1": () => ({ status: 500, body: { detail: "Database is busy." } }),
        });
        render(<Home />);
        await screen.findByText("Roadmap card");
        await userEvent.click(screen.getByRole("button", { name: "Board settings" }));
        await userEvent.click(screen.getByRole("button", { name: "Save" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Database is busy.");
        expect(screen.getByRole("dialog", { name: "Board settings" })).toBeInTheDocument();
    });

    it("deletes a board only after confirming, then opens another", async () => {
        let boards = [summary("1", "Roadmap", 1), summary("2", "Hiring", 1)];
        const server = installServer({
            ...twoBoards,
            "GET /api/boards": () => ({ body: boards }),
            "DELETE /api/boards/1": () => {
                boards = boards.filter((item) => item.id !== "1");
                return { body: { status: "ok" } };
            },
        });
        render(<Home />);
        await screen.findByText("Roadmap card");

        await userEvent.click(screen.getByRole("button", { name: "Board settings" }));
        const dialog = screen.getByRole("dialog", { name: "Board settings" });
        await userEvent.click(within(dialog).getByRole("button", { name: "Delete board" }));
        expect(server.count("DELETE /api/boards/1")).toBe(0);
        expect(within(dialog).getByText(/cannot be undone/)).toBeInTheDocument();
        await userEvent.click(within(dialog).getByRole("button", { name: "Delete board" }));

        expect(await screen.findByText("Hiring card")).toBeInTheDocument();
        expect(server.count("DELETE /api/boards/1")).toBe(1);
    });

    it("offers to create a board when there are none", async () => {
        let boards: ReturnType<typeof summary>[] = [];
        const server = installServer({
            ...signedIn,
            "GET /api/boards": () => ({ body: boards }),
            "POST /api/boards": () => {
                boards = [summary("4", "First")];
                return { body: { id: "4" } };
            },
            "GET /api/boards/4": () => ({ body: namedBoard("4", "First") }),
        });
        render(<Home />);

        await userEvent.click(await screen.findByRole("button", { name: /create a board/i }));
        await userEvent.type(screen.getByLabelText("Name"), "First");
        await userEvent.click(screen.getByRole("button", { name: "Create board" }));

        expect(await screen.findByLabelText("Column title")).toHaveValue("Backlog");
        expect(server.bodies("POST /api/boards")[0]).toMatchObject({ title: "First", template: "basic" });
    });

    it("shows a retry when the board list cannot be loaded", async () => {
        let attempts = 0;
        installServer({
            ...signedIn,
            "GET /api/boards": () => {
                attempts += 1;
                return attempts === 1 ? { status: 500, body: {} } : { body: [summary("1", "My Board")] };
            },
            "GET /api/boards/1": () => ({ body: emptyBoard }),
        });
        render(<Home />);

        expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load your boards");
        await userEvent.click(screen.getByRole("button", { name: /try again/i }));
        expect(await screen.findByLabelText("Column title")).toBeInTheDocument();
    });
});

describe("Account settings", () => {
    const openAccount = async () => {
        await userEvent.click(await screen.findByRole("button", { name: "Account settings" }));
        return screen.getByRole("dialog", { name: "Account settings" });
    };

    const withBoard: Record<string, Handler> = {
        ...signedIn,
        "GET /api/boards/1": () => ({ body: emptyBoard }),
    };

    it("saves the display name and shows it in the header", async () => {
        const server = installServer({
            ...withBoard,
            "PATCH /api/me": () => ({ body: { id: "1", username: "user", displayName: "Demo Person" } }),
        });
        render(<Home />);
        const dialog = await openAccount();
        expect(within(dialog).getByText("user")).toBeInTheDocument();
        await userEvent.type(within(dialog).getByLabelText("Name"), "Demo Person");
        await userEvent.click(within(dialog).getByRole("button", { name: "Save name" }));

        expect(await within(dialog).findByText("Saved.")).toBeInTheDocument();
        expect(server.bodies("PATCH /api/me")).toEqual([{ display_name: "Demo Person" }]);
        expect(screen.getByRole("button", { name: "Account settings" })).toHaveTextContent("Demo Person");
    });

    it("changes the password", async () => {
        const server = installServer({
            ...withBoard,
            "POST /api/me/password": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        const dialog = await openAccount();
        await userEvent.type(within(dialog).getByLabelText("Current password"), "password");
        await userEvent.type(within(dialog).getByLabelText("New password"), "better-pass");
        await userEvent.type(within(dialog).getByLabelText("Confirm new password"), "better-pass");
        await userEvent.click(within(dialog).getByRole("button", { name: "Change password" }));

        expect(await within(dialog).findByText(/other devices have been signed out/i)).toBeInTheDocument();
        expect(server.bodies("POST /api/me/password")).toEqual([
            { current_password: "password", new_password: "better-pass" },
        ]);
        expect(within(dialog).getByLabelText("Current password")).toHaveValue("");
    });

    it("stays signed in when the current password is wrong", async () => {
        installServer({
            ...withBoard,
            "POST /api/me/password": () => ({
                status: 403,
                body: { detail: "That password is not correct." },
            }),
        });
        render(<Home />);
        const dialog = await openAccount();
        await userEvent.type(within(dialog).getByLabelText("Current password"), "nope");
        await userEvent.type(within(dialog).getByLabelText("New password"), "better-pass");
        await userEvent.type(within(dialog).getByLabelText("Confirm new password"), "better-pass");
        await userEvent.click(within(dialog).getByRole("button", { name: "Change password" }));

        expect(await within(dialog).findByRole("alert")).toHaveTextContent("That password is not correct.");
        expect(screen.queryByText("Welcome back")).not.toBeInTheDocument();
    });

    it("checks that the new passwords match", async () => {
        const server = installServer(withBoard);
        render(<Home />);
        const dialog = await openAccount();
        await userEvent.type(within(dialog).getByLabelText("Current password"), "password");
        await userEvent.type(within(dialog).getByLabelText("New password"), "better-pass");
        await userEvent.type(within(dialog).getByLabelText("Confirm new password"), "other-pass");
        await userEvent.click(within(dialog).getByRole("button", { name: "Change password" }));

        expect(within(dialog).getByRole("alert")).toHaveTextContent("do not match");
        expect(server.count("POST /api/me/password")).toBe(0);
    });

    it("deletes the account after confirming with the password", async () => {
        const server = installServer({
            ...withBoard,
            "DELETE /api/me": () => ({ body: { status: "ok" } }),
        });
        render(<Home />);
        const dialog = await openAccount();
        await userEvent.click(within(dialog).getByRole("button", { name: "Delete account" }));
        await userEvent.type(within(dialog).getByLabelText(/enter your password/i), "password");
        await userEvent.click(within(dialog).getByRole("button", { name: "Delete account" }));

        expect(await screen.findByText("Welcome back")).toBeInTheDocument();
        expect(screen.getByRole("alert")).toHaveTextContent("Your account has been deleted.");
        expect(server.bodies("DELETE /api/me")).toEqual([{ password: "password" }]);
    });

    it("closes with Escape", async () => {
        installServer(withBoard);
        render(<Home />);
        await openAccount();
        await userEvent.keyboard("{Escape}");
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
});
