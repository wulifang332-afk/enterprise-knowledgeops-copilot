import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const outputDir = path.resolve(repoRoot, "docs/assets/studio");
const port = process.env.STUDIO_SCREENSHOT_PORT ?? "4174";
const baseURL = `http://127.0.0.1:${port}`;

const routes = [
  { path: "/", heading: "Enterprise KnowledgeOps Studio", filename: "studio-landing.png" },
  { path: "/workspace", heading: "Knowledge Workspace", filename: "studio-workspace.png" },
  { path: "/search", heading: "Search & Citations", filename: "studio-search.png" },
  { path: "/query", heading: "Query Planner", filename: "studio-query.png" },
  { path: "/readiness", heading: "Readiness Center", filename: "studio-readiness.png" },
  { path: "/evaluation", heading: "Evaluation Center", filename: "studio-evaluation.png" },
  { path: "/governance", heading: "Governance Center", filename: "studio-governance.png" },
  { path: "/graph", heading: "Graph Explorer", filename: "studio-graph.png" }
];

await mkdir(outputDir, { recursive: true });

const server = spawn("npm", ["run", "dev", "--", "--port", port, "--strictPort"], {
  cwd: frontendRoot,
  env: { ...process.env, BROWSER: "none" },
  stdio: ["ignore", "pipe", "pipe"]
});

server.stdout.on("data", (chunk) => {
  process.stdout.write(`[studio-screenshots] ${chunk}`);
});
server.stderr.on("data", (chunk) => {
  process.stderr.write(`[studio-screenshots] ${chunk}`);
});

try {
  await waitForServer(baseURL);

  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1
  });

  for (const route of routes) {
    await page.goto(`${baseURL}${route.path}`, { waitUntil: "domcontentloaded" });
    await page.getByRole("heading", { level: 1, name: route.heading }).waitFor({ state: "visible" });
    await page.waitForTimeout(500);
    await page.screenshot({
      path: path.join(outputDir, route.filename),
      fullPage: true
    });
    console.log(`captured ${route.filename}`);
  }

  await browser.close();
} finally {
  server.kill("SIGTERM");
}

async function waitForServer(url) {
  const startedAt = Date.now();
  let lastError;

  while (Date.now() - startedAt < 120_000) {
    if (server.exitCode !== null) {
      throw new Error(`Vite server exited before becoming ready with code ${server.exitCode}`);
    }

    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch (error) {
      lastError = error;
    }

    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`Timed out waiting for ${url}: ${lastError instanceof Error ? lastError.message : "unknown error"}`);
}
