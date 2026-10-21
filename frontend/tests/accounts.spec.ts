import { expect, test, type Page } from "@playwright/test";

// Every test signs up its own account, so it can change or delete it freely.
test.use({ storageState: { cookies: [], origins: [] } });

const PASSWORD = "e2e-password";

const uniqueName = () => `e2e-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

const signUp = async (page: Page, username: string) => {
  await page.goto("/");
  await page.getByRole("button", { name: /create an account/i }).click();
  await page.getByLabel("Username").fill(username);
  await page.getByLabel(/^Name/).fill("E2E Person");
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
};

const deleteAccount = async (page: Page) => {
  await page.getByRole("button", { name: "Account settings" }).click();
  const dialog = page.getByRole("dialog", { name: "Account settings" });
  await dialog.getByRole("button", { name: "Delete account" }).click();
  await dialog.getByLabel(/enter your password/i).fill(PASSWORD);
  await dialog.getByRole("button", { name: "Delete account" }).click();
  await expect(page.getByText("Welcome back")).toBeVisible();
};

const switcher = (page: Page) => page.getByRole("button", { name: /switch board/i });

test("sign up, manage boards, and delete the account", async ({ page }) => {
  const username = uniqueName();
  await signUp(page, username);
  await expect(page.getByRole("button", { name: "Account settings" })).toContainText("E2E Person");
  await expect(switcher(page)).toContainText("My Board");

  // Create a second board from the basic template.
  await switcher(page).click();
  await page.getByRole("menuitem", { name: /new board/i }).click();
  const dialog = page.getByRole("dialog", { name: "New board" });
  await dialog.getByLabel("Name").fill("Launch plan");
  await dialog.getByRole("button", { name: "Create board" }).click();
  await expect(switcher(page)).toContainText("Launch plan");
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(3);

  // Add a card on the new board; it must not appear on the first one.
  const todo = page.locator('[data-testid^="column-"]').first();
  await todo.getByRole("button", { name: /add a card/i }).click();
  await todo.getByPlaceholder("Card title").fill("Only on launch");
  await todo.getByRole("button", { name: /add card/i }).click();
  await expect(todo.getByText("Only on launch")).toBeVisible();

  await switcher(page).click();
  await page.getByRole("menuitemradio", { name: /my board/i }).click();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
  await expect(page.getByText("Only on launch")).toHaveCount(0);

  // The last board opened is the one shown after a reload.
  await switcher(page).click();
  await page.getByRole("menuitemradio", { name: /launch plan/i }).click();
  await page.reload();
  await expect(switcher(page)).toContainText("Launch plan");
  await expect(page.getByText("Only on launch")).toBeVisible();

  // Rename it, then delete it.
  await page.getByRole("button", { name: "Board settings" }).click();
  const settings = page.getByRole("dialog", { name: "Board settings" });
  await settings.getByLabel("Name").fill("Launch v2");
  await settings.getByRole("button", { name: "Save" }).click();
  await expect(switcher(page)).toContainText("Launch v2");

  await page.getByRole("button", { name: "Board settings" }).click();
  await settings.getByRole("button", { name: "Delete board" }).click();
  await settings.getByRole("button", { name: "Delete board" }).click();
  await expect(switcher(page)).toContainText("My Board");
  await switcher(page).click();
  await expect(page.getByRole("menuitemradio")).toHaveCount(1);
  await page.keyboard.press("Escape");

  await deleteAccount(page);
  await page.getByPlaceholder("user").fill(username);
  await page.getByPlaceholder("password").fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator("p[role=alert]")).toContainText("Incorrect username or password.");
});

test("changing the password signs out other devices", async ({ page, browser }) => {
  const username = uniqueName();
  await signUp(page, username);

  const other = await browser.newContext({ storageState: await page.context().storageState() });
  const otherPage = await other.newPage();
  await otherPage.goto("/");
  await expect(otherPage.locator('[data-testid^="column-"]').first()).toBeVisible();

  await page.getByRole("button", { name: "Account settings" }).click();
  const dialog = page.getByRole("dialog", { name: "Account settings" });
  await dialog.getByLabel("Current password").fill(PASSWORD);
  await dialog.getByLabel("New password", { exact: true }).fill(`${PASSWORD}-2`);
  await dialog.getByLabel("Confirm new password").fill(`${PASSWORD}-2`);
  await dialog.getByRole("button", { name: "Change password" }).click();
  await expect(dialog.getByText(/other devices have been signed out/i)).toBeVisible();
  await page.keyboard.press("Escape");

  // This device keeps working; the other one is sent back to sign in.
  await page.reload();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await otherPage.reload();
  await expect(otherPage.getByText("Welcome back")).toBeVisible();
  await other.close();

  await page.getByRole("button", { name: "Account settings" }).click();
  const settings = page.getByRole("dialog", { name: "Account settings" });
  await settings.getByRole("button", { name: "Delete account" }).click();
  await settings.getByLabel(/enter your password/i).fill(`${PASSWORD}-2`);
  await settings.getByRole("button", { name: "Delete account" }).click();
  await expect(page.getByText("Welcome back")).toBeVisible();
});
