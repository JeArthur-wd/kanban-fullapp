import { expect, test, type Locator, type Page } from "@playwright/test";

const TEST_PREFIX = "E2E ";

const login = async (page: Page) => {
  await page.goto("/");
  await page.getByPlaceholder("user").fill("user");
  await page.getByPlaceholder("password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

const getColumnByTitle = (page: Page, title: string) =>
  page.locator('[data-testid^="column-"]').filter({
    has: page.locator(`input[aria-label="Column title"][value="${title}"]`),
  });

type ApiBoard = {
  columns: Array<{ id: string; title: string; cardIds: string[] }>;
  cards: Record<string, { id: string; title: string }>;
};

const readBoard = async (page: Page): Promise<ApiBoard> => {
  const response = await page.request.get("/api/board");
  expect(response.ok()).toBeTruthy();
  return response.json();
};

// Cards are created through the API so each test controls exactly what is on the board.
const createCard = async (page: Page, columnTitle: string, title: string) => {
  const board = await readBoard(page);
  const column = board.columns.find((item) => item.title === columnTitle);
  if (!column) throw new Error(`No column named ${columnTitle}`);
  const response = await page.request.post("/api/cards", {
    data: { column_id: Number(column.id), title },
  });
  expect(response.ok()).toBeTruthy();
};

const removeTestCards = async (page: Page) => {
  const board = await readBoard(page);
  for (const card of Object.values(board.cards)) {
    if (card.title.startsWith(TEST_PREFIX) || card.title === "Playwright card") {
      await page.request.delete(`/api/cards/${card.id}`);
    }
  }
};

const cardTitles = (column: Locator) => column.locator("article h4").allTextContents();

test.afterEach(async ({ page }) => {
  // The page has a session only if the test signed in.
  if ((await page.request.get("/api/session")).ok()) {
    await removeTestCards(page);
  }
});

test("loads the kanban board", async ({ page }) => {
  await login(page);
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("rejects a wrong password", async ({ page }) => {
  await page.goto("/");
  await page.getByPlaceholder("user").fill("user");
  await page.getByPlaceholder("password").fill("not-the-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  // Next also renders an empty role="alert" route announcer, so target the form message.
  await expect(page.locator("p[role=alert]")).toContainText("Incorrect username or password.");
  await expect(page.getByText("Welcome back")).toBeVisible();
});

test("the API is closed to anyone who has not signed in", async ({ request }) => {
  expect((await request.get("/api/board")).status()).toBe(401);
  expect((await request.get("/api/board", { headers: { "X-User": "user" } })).status()).toBe(401);
  expect((await request.post("/api/chat", { data: { message: "hi" } })).status()).toBe(401);
});

test("static files outside the site folder are not served", async ({ request }) => {
  const response = await request.get("/%2e%2e/%2e%2e/%2e%2e/etc/passwd");
  expect(await response.text()).not.toContain("root:");
});

test("keeps the session after a reload and ends it on log out", async ({ page }) => {
  await login(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.getByText("Welcome back")).toHaveCount(0);

  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByText("Welcome back")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Welcome back")).toBeVisible();
});

test("adds and deletes a card", async ({ page }) => {
  await login(page);
  const column = getColumnByTitle(page, "Backlog");
  await column.getByRole("button", { name: /add a card/i }).click();
  await column.getByPlaceholder("Card title").fill("Playwright card");
  await column.getByPlaceholder("Details").fill("Added via e2e.");
  await column.getByRole("button", { name: /add card/i }).click();
  await expect(column.getByText("Playwright card").first()).toBeVisible();

  // The draggable card is itself role="button", so match the delete control by its label.
  await column.locator('button[aria-label="Delete Playwright card"]').click();
  await expect(column.getByText("Playwright card")).toHaveCount(0);
});

test("renames a column once and keeps the name after a reload", async ({ page }) => {
  await login(page);
  const patches: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "PATCH" && request.url().includes("/api/columns/")) {
      patches.push(request.postData() ?? "");
    }
  });

  // The Done column is the last one. Locate by position: the value attribute changes as you type.
  const input = page.getByLabel("Column title").last();
  await expect(input).toHaveValue("Done");
  await input.fill("Shipped");
  await input.press("Enter");
  await expect.poll(() => patches.length).toBe(1);
  expect(patches[0]).toContain("Shipped");

  await page.reload();
  const renamed = page.getByLabel("Column title").last();
  await expect(renamed).toHaveValue("Shipped");
  await renamed.fill("Done");
  await renamed.press("Enter");
  await page.reload();
  await expect(page.getByLabel("Column title").last()).toHaveValue("Done");
});

const dragCard = async (page: Page, card: Locator, target: Locator, targetY: number) => {
  const cardBox = await card.boundingBox();
  const targetBox = await target.boundingBox();
  if (!cardBox || !targetBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }
  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(targetBox.x + targetBox.width / 2, targetY, { steps: 12 });
  await page.mouse.up();
};

test("moves a card between columns", async ({ page }) => {
  await login(page);
  await createCard(page, "Backlog", `${TEST_PREFIX}cross-column`);
  await page.reload();

  const card = page.locator("article", { hasText: `${TEST_PREFIX}cross-column` }).first();
  const targetColumn = getColumnByTitle(page, "Review");
  await expect(card).toBeVisible();
  const columnBox = await targetColumn.boundingBox();
  if (!columnBox) throw new Error("Unable to resolve drag coordinates.");
  await dragCard(page, card, targetColumn, columnBox.y + 120);

  await expect(targetColumn.getByText(`${TEST_PREFIX}cross-column`)).toBeVisible();
  // The move is saved, not just drawn.
  await page.reload();
  await expect(getColumnByTitle(page, "Review").getByText(`${TEST_PREFIX}cross-column`)).toBeVisible();
});

test("moves a card down within its own column and keeps it there", async ({ page }) => {
  await login(page);
  for (const name of ["one", "two", "three"]) {
    await createCard(page, "Discovery", `${TEST_PREFIX}${name}`);
  }
  await page.reload();

  const column = getColumnByTitle(page, "Discovery");
  const one = column.locator("article", { hasText: `${TEST_PREFIX}one` });
  const three = column.locator("article", { hasText: `${TEST_PREFIX}three` });
  await expect(three).toBeVisible();
  const threeBox = await three.boundingBox();
  if (!threeBox) throw new Error("Unable to resolve drag coordinates.");
  await dragCard(page, one, three, threeBox.y + threeBox.height - 4);

  const expected = [`${TEST_PREFIX}two`, `${TEST_PREFIX}three`, `${TEST_PREFIX}one`];
  await expect.poll(async () => (await cardTitles(column)).filter((t) => t.startsWith(TEST_PREFIX))).toEqual(expected);
  await page.reload();
  const reloaded = getColumnByTitle(page, "Discovery");
  await expect.poll(async () => (await cardTitles(reloaded)).filter((t) => t.startsWith(TEST_PREFIX))).toEqual(expected);
});

test("moves a card with the keyboard", async ({ page }) => {
  await login(page);
  for (const name of ["first", "second"]) {
    await createCard(page, "Discovery", `${TEST_PREFIX}${name}`);
  }
  await page.reload();

  const column = getColumnByTitle(page, "Discovery");
  const first = column.locator("article", { hasText: `${TEST_PREFIX}first` });
  await expect(first).toBeVisible();
  await first.focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Space");

  const expected = [`${TEST_PREFIX}second`, `${TEST_PREFIX}first`];
  await expect.poll(async () => (await cardTitles(column)).filter((t) => t.startsWith(TEST_PREFIX))).toEqual(expected);
  await page.reload();
  const reloaded = getColumnByTitle(page, "Discovery");
  await expect.poll(async () => (await cardTitles(reloaded)).filter((t) => t.startsWith(TEST_PREFIX))).toEqual(expected);
});
