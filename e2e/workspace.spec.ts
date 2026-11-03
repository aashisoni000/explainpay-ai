import { expect, test } from "@playwright/test";

test("workspace navigation and mobile menu are functional", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/transactions");
  await expect(page.getByRole("heading", { name: "Upload transactions" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload & preview" })).toBeDisabled();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: /Website scanner/i }).click();
  await expect(page).toHaveURL(/\/website-scanner$/);
  await expect(page.getByRole("textbox", { name: "Website URL" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
});

test("scanner validates input and displays actual missing-model errors", async ({ page, request }) => {
  const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
  const status = await request.get(`${apiUrl}/api/system/status`);
  expect(status.ok()).toBe(true);
  const system = await status.json();
  test.skip(system.models.phishing.available, "Requires missing-model mode; real model is available.");
  await page.goto("/website-scanner");
  const input = page.getByRole("textbox", { name: "Website URL" });
  await input.fill("https://example.com");
  await page.getByRole("button", { name: "Analyze website" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toContainText(/API 503: Required ML model is unavailable; train and configure its artifacts/);
});

test("CSV upload persists preview and reports actual model state", async ({ page, request }) => {
  const apiUrl = process.env.E2E_API_URL ?? "http://localhost:8000";
  const status = await request.get(`${apiUrl}/api/system/status`);
  expect(status.ok()).toBe(true);
  const system = await status.json();
  await page.goto("/transactions");
  const columns = ["Time", ...Array.from({ length: 28 }, (_, i) => `V${i + 1}`), "Amount"];
  const csv = `${columns.join(",")}\n${columns.map((key) => key === "Amount" ? "12.5" : "0").join(",")}\n`;
  // Explicit synthetic test fixture verifies upload mechanics, not model validity.
  await page.getByLabel("Transaction CSV", { exact: true }).setInputFiles({
    name: "SYNTHETIC_BROWSER_TEST_ONLY.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.getByRole("button", { name: "Upload & preview" }).click();
  await expect(page.getByRole("button", { name: "Analyze transactions" })).toBeVisible();
  await expect(page.getByText("SYNTHETIC_BROWSER_TEST_ONLY.csv").first()).toBeVisible();
  await page.getByRole("button", { name: "Analyze transactions" }).click();
  if (system.models.fraud.available) {
    await expect(page.getByRole("heading", { name: "Transaction results" })).toBeVisible();
    await page.getByRole("link", { name: /^Explain / }).first().click();
    await expect(page.getByRole("heading", { name: "Feature contributions" })).toBeVisible();
  } else {
    await expect(page.getByRole("main").getByRole("alert")).toContainText(/API 503: Required ML model is unavailable; train and configure its artifacts/);
  }
});

test("API network failures have visible error states", async ({ page }) => {
  await page.route("**/api/transactions/history", (route) => route.abort("connectionrefused"));
  await page.goto("/transactions");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(/connect|network|fetch|reach/i);
});

test("history reports and status routes render live service data", async ({ page }) => {
  for (const route of ["/investigations", "/reports", "/settings"]) {
    await page.goto(route);
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }
  await expect(page.getByText(/Model evaluation & runtime metrics/)).toBeVisible();
});
