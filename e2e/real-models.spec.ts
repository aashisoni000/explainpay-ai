import { expect, test } from "@playwright/test";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";

const sample = path.resolve("data/processed/ulb_sample_transactions.csv");
const trained = existsSync("data/models/fraud.joblib") && existsSync("data/models/phishing.joblib");

test.describe("actual Kaggle-trained models", () => {
  test.skip(!trained || !existsSync(sample), "Requires actual trained artifacts and the locally sourced ULB sample.");

  test("real upload to SHAP detail, persisted history, and PDF download", async ({ page }) => {
    await page.goto("/transactions");
    await page.getByLabel("Transaction CSV", { exact: true }).setInputFiles(sample);
    await page.getByRole("button", { name: "Upload & preview" }).click();
    await page.getByRole("button", { name: "Analyze transactions" }).click();
    await expect(page.getByRole("heading", { name: "Transaction results" })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("link", { name: /^Explain / })).toHaveCount(10);
    await page.getByRole("link", { name: /^Explain / }).first().click();
    await expect(page.getByRole("heading", { name: "Feature contributions" })).toBeVisible();
    const detailUrl = page.url();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Feature contributions" })).toBeVisible();
    await expect(page.getByText(/Base value \(log-odds\)/)).toBeVisible();
    await page.getByRole("button", { name: "Generate PDF report" }).click();
    const downloadEvent = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download report", exact: true }).click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
    expect(await download.failure()).toBeNull();
    const pdfPath = await download.path();
    expect(pdfPath).not.toBeNull();
    expect((await readFile(pdfPath!)).subarray(0, 5).toString()).toBe("%PDF-");
    await page.goto("/investigations");
    await expect(page.getByRole("main").getByRole("link", { name: /ulb_sample_transactions/ }).first()).toBeVisible();
    await page.goto(detailUrl);
    await expect(page.getByRole("heading", { name: "Feature contributions" })).toBeVisible();
  });

  test("real phishing prediction, provider states, saved scan, and PDF", async ({ page }) => {
    await page.goto("/website-scanner");
    await page.getByRole("textbox", { name: "Website URL" }).fill("https://example.com");
    await page.getByRole("button", { name: "Analyze website" }).click();
    await expect(page).toHaveURL(/\/website-scanner\/[a-f0-9-]+$/, { timeout: 30000 });
    await expect(page.getByRole("heading", { name: "Feature contributions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Threat intelligence providers" })).toBeVisible();
    await expect(page.getByText(/ML prediction:/)).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Feature contributions" })).toBeVisible();
    await page.getByRole("button", { name: "Generate PDF report" }).click();
    const downloadEvent = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download report", exact: true }).click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toMatch(/\.pdf$/);
    const pdfPath = await download.path();
    expect(pdfPath).not.toBeNull();
    expect((await readFile(pdfPath!)).subarray(0, 5).toString()).toBe("%PDF-");
  });

  test("both real evaluation reports include held-out metrics and limitations", async ({ page }) => {
    await page.goto("/settings");
    const phishing = page.getByRole("heading", { name: "Website phishing model evaluation" }).locator("..");
    await expect(phishing.getByText("Phishing detection rate").first()).toBeVisible();
    await expect(phishing.getByRole("listitem").filter({ hasText: /high phishing prevalence inflates/ })).toBeVisible();
    await expect(page.getByText("Fraud detection rate").first()).toBeVisible();
    await expect(phishing.getByText("22.6%", { exact: true }).first()).toBeVisible();
  });
});
