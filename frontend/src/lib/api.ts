import type { BoardData, Card, Column } from "@/lib/kanban";
import { toCardId, toColumnId } from "@/lib/kanban";

type BoardResponse = {
    board: { id: string; title: string };
    columns: Array<Column & { position?: number } & { cardIds: string[] }>;
    cards: Record<string, Card>;
};

type ApiOptions = {
    // The login and session calls report 401 themselves instead of ending the session.
    handleUnauthorized?: boolean;
};

export type ChatMessage = {
    role: "user" | "assistant";
    content: string;
    // Error notices shown in the chat are not real replies and are not sent back to the model.
    isError?: boolean;
};

export class ApiError extends Error {
    status: number;
    detail: string | null;

    constructor(status: number, detail: string | null) {
        super(detail ?? `Request failed (${status})`);
        this.status = status;
        this.detail = detail;
    }
}

let unauthorizedHandler: (() => void) | null = null;

export const setUnauthorizedHandler = (handler: (() => void) | null) => {
    unauthorizedHandler = handler;
};

const readDetail = async (response: Response): Promise<string | null> => {
    try {
        const body = JSON.parse(await response.text());
        return typeof body?.detail === "string" ? body.detail : null;
    } catch {
        return null;
    }
};

type ChatAction = {
    type: "create_card" | "update_card" | "move_card" | "delete_card";
    [key: string]: unknown;
};

type ChatResponse = {
    response: string;
    actions: ChatAction[];
    skipped?: Array<{ type: string; reason: string }>;
    board?: BoardResponse;
    model?: string | null;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";
const DEFAULT_TIMEOUT = 30000;

const apiFetch = async <T>(
    path: string,
    options: RequestInit = {},
    apiOptions: ApiOptions = {}
): Promise<T> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);

    try {
        const headers = new Headers(options.headers);
        headers.set("Content-Type", "application/json");

        const response = await fetch(`${apiBase}${path}`, {
            ...options,
            headers,
            signal: controller.signal,
        });

        if (!response.ok) {
            if (response.status === 401 && apiOptions.handleUnauthorized !== false) {
                unauthorizedHandler?.();
            }
            throw new ApiError(response.status, await readDetail(response));
        }

        if (response.status === 204) {
            return undefined as T;
        }

        return (await response.json()) as T;
    } finally {
        clearTimeout(timeoutId);
    }
};

export const toBoardData = (payload: BoardResponse): BoardData => {
    const cards: Record<string, Card> = Object.fromEntries(
        Object.entries(payload.cards).map(([id, card]) => [
            toCardId(id),
            { ...card, id: toCardId(card.id) },
        ])
    );

    return {
        columns: payload.columns.map((column) => ({
            id: toColumnId(column.id),
            title: column.title,
            cardIds: column.cardIds.map((cardId) => toCardId(cardId)),
        })),
        cards,
    };
};

export const login = (username: string, password: string) =>
    apiFetch<{ username: string }>(
        "/api/login",
        { method: "POST", body: JSON.stringify({ username, password }) },
        { handleUnauthorized: false }
    );

export const logout = () => apiFetch("/api/logout", { method: "POST" });

export const fetchSession = () =>
    apiFetch<{ username: string }>("/api/session", {}, { handleUnauthorized: false });

export const fetchBoard = () => apiFetch<BoardResponse>("/api/board");

export const updateColumn = (
    columnId: number,
    payload: { title?: string; position?: number }
) =>
    apiFetch(`/api/columns/${columnId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    });

export const createCard = (payload: {
    column_id: number;
    title: string;
    details: string;
    position?: number;
}) =>
    apiFetch<{ id: string }>("/api/cards", {
        method: "POST",
        body: JSON.stringify(payload),
    });

export const updateCard = (
    cardId: number,
    payload: { title?: string; details?: string; column_id?: number; position?: number }
) =>
    apiFetch(`/api/cards/${cardId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    });

export const deleteCard = (cardId: number) =>
    apiFetch(`/api/cards/${cardId}`, { method: "DELETE" });

export const sendChat = (payload: {
    message: string;
    history: ChatMessage[];
    apply_updates: boolean;
}) =>
    apiFetch<ChatResponse>("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
    });
