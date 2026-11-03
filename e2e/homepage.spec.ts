import { expect, test } from "@playwright/test";

test("homepage preserves shader and accessible investigation navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Know the risk. Understand the reason." })).toBeVisible();
  const transactionLink = page.getByRole("link", { name: /Detect Financial Fraud/ });
  const websiteLink = page.getByRole("link", { name: /Check Website Trust/ });
  await expect(transactionLink).toHaveAttribute("href", "/transactions");
  await expect(websiteLink).toHaveAttribute("href", "/website-scanner");
  await page.keyboard.press("Tab");
  await expect(transactionLink).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(websiteLink).toBeFocused();
  await websiteLink.click();
  await expect(page).toHaveURL(/\/website-scanner$/);
  await expect(page.getByRole("main")).toBeVisible();
});

test("reduced motion is static and mobile viewport has no horizontal overflow", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("canvas")).toHaveAttribute("data-renderer-status", /static|unavailable/);
  const hasOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  expect(hasOverflow).toBe(false);
});

test("homepage remains usable when WebGL is unavailable", async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, type: string, ...args: unknown[]) {
      if (["webgl", "webgl2", "experimental-webgl"].includes(type)) return null;
      return Reflect.apply(original, this, [type, ...args]);
    } as typeof HTMLCanvasElement.prototype.getContext;
  });
  await page.goto("/");
  await expect(page.locator("canvas")).toHaveAttribute("data-renderer-status", "unavailable");
  await expect(page.getByRole("link", { name: /Detect Financial Fraud/ })).toBeVisible();
});
