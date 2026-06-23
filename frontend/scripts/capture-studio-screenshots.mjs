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

await mkdir(outputDir, { recursive: true });

const server = spawn("npm", ["run", "dev", "--", "--port", port, "--strictPort"], {
  cwd: frontendRoot,
  env: { ...process.env, BROWSER: "none" },
  stdio: ["ignore", "pipe", "pipe"]
});

server.stdout.on("data", (chunk) => {
  process.stdout.write(`[agent-workbench-screenshot] ${chunk}`);
});
server.stderr.on("data", (chunk) => {
  process.stderr.write(`[agent-workbench-screenshot] ${chunk}`);
});

try {
  await waitForServer(baseURL);

  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1
  });

  await page.goto(baseURL, { waitUntil: "domcontentloaded" });
  await page
    .getByRole("heading", { level: 1, name: "Enterprise KnowledgeOps Agent Workbench" })
    .waitFor({ state: "visible" });
  await page.waitForTimeout(500);
  await page.screenshot({
    path: path.join(outputDir, "agent-workbench.png"),
    fullPage: true
  });
  console.log("captured agent-workbench.png");

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
