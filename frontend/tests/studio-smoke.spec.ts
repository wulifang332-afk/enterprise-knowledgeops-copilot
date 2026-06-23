import { expect, test } from "@playwright/test";

test.describe("Enterprise KnowledgeOps Agent Workbench", () => {
  test("renders the simplified interview demo and core workflow sections", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => {
      pageErrors.push(error.message);
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", { level: 1, name: "Enterprise KnowledgeOps Agent Workbench" })
    ).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Query" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Tool trace" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Citation-backed answer" })).toBeVisible();
    await expect(page.getByText("search_documents")).toBeVisible();
    await expect(page.getByText("run_evaluation")).toBeVisible();

    await page.getByRole("button", { name: "Evaluation" }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Evaluation" })).toBeVisible();

    await page.getByRole("button", { name: "Architecture" }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Architecture" })).toBeVisible();

    await page.waitForTimeout(100);
    expect(pageErrors).toEqual([]);
  });

  test("keeps the core workflow readable on mobile", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => {
      pageErrors.push(error.message);
    });

    await page.setViewportSize({ width: 390, height: 900 });
    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", { level: 1, name: "Enterprise KnowledgeOps Agent Workbench" })
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Run agent" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Tool trace" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Citation-backed answer" })).toBeVisible();

    await page.waitForTimeout(100);
    expect(pageErrors).toEqual([]);
  });
});
