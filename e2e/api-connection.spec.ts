import { expect, test } from "@playwright/test";

test("same-origin API proxy serves both histories and system readiness", async ({ request }) => {
  for (const endpoint of ["transactions/history", "websites/history"]) {
    const response = await request.get(`/backend/api/${endpoint}`);
    expect(response.status()).toBe(200);
    expect(Array.isArray(await response.json())).toBe(true);
  }
  const response = await request.get("/backend/api/system/status");
  expect(response.status()).toBe(200);
  expect((await response.json()).database.available).toBe(true);
});

test("both workspaces load without direct browser access to backend ports", async ({ page }) => {
  await page.route(/https?:\/\/(?:localhost|127\.0\.0\.1):800[01]\//, (route) => route.abort());
  for (const route of ["/transactions", "/website-scanner"]) {
    const response = page.waitForResponse((response) =>
      response.url().includes("/backend/api/") && response.url().endsWith("/history"),
    );
    await page.goto(route);
    expect((await response).status()).toBe(200);
    await expect(page.getByRole("main").getByRole("status")).toHaveCount(0);
    await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
  }
});
