import { expect, test } from "@playwright/test";

const routes = [
  { path: "/", heading: "Enterprise KnowledgeOps Studio" },
  { path: "/workspace", heading: "Knowledge Workspace" },
  { path: "/search", heading: "Search & Citations" },
  { path: "/graph", heading: "Graph Explorer" },
  { path: "/query", heading: "Query Planner" },
  { path: "/evaluation", heading: "Evaluation Center" },
  { path: "/governance", heading: "Governance Center" }
] as const;

test.describe("Enterprise KnowledgeOps Studio smoke routes", () => {
  for (const route of routes) {
    test(`${route.path} renders the Studio shell and page heading`, async ({ page }) => {
      const pageErrors: string[] = [];
      page.on("pageerror", (error) => {
        pageErrors.push(error.message);
      });

      await page.goto(route.path, { waitUntil: "domcontentloaded" });

      await expect(page.getByText("Enterprise KnowledgeOps Studio").first()).toBeVisible();
      await expect(page.getByRole("navigation", { name: "Primary navigation" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 1, name: route.heading })).toBeVisible();

      await page.waitForTimeout(100);
      expect(pageErrors).toEqual([]);
    });
  }
});
