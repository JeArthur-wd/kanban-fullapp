import { expect, test as setup } from "@playwright/test";
import { STORAGE_STATE } from "../playwright.config";

setup("sign in as the demo user", async ({ request }) => {
  const response = await request.post("/api/login", {
    data: { username: "user", password: "password" },
  });
  expect(response.ok()).toBeTruthy();
  await request.storageState({ path: STORAGE_STATE });
});
