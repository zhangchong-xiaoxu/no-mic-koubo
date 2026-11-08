// Step 4: screenshot real pages with a headless Chromium browser over CDP (Node 22+, no dependencies).
// node shot.mjs shots.json
// shots.json: [{ url, out, width?, height?, dpr?, fullPage?, waitMs?, steps?: [js...], clip?: {x,y,w,h} }]
// Browser: BROWSER env var, else common Edge/Chrome install paths.
import { spawn } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, mkdtempSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

const CANDIDATES = [
  process.env.BROWSER,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);
const BROWSER = CANDIDATES.find((p) => existsSync(p));
if (!BROWSER) throw new Error("No Chromium browser found; set BROWSER=/path/to/chrome");

const jobs = JSON.parse(readFileSync(process.argv[2] ?? "shots.json", "utf8"));
const port = 9333;
const profile = mkdtempSync(join(tmpdir(), "cdp-"));
const proc = spawn(BROWSER, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--hide-scrollbars", "--lang=zh-CN", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let page;
for (let i = 0; i < 50 && !page; i++) {
  try { page = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {}
  if (!page) await sleep(200);
}
if (!page) { proc.kill(); throw new Error("browser did not start"); }

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pending = new Map();
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expression) => {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 400));
  return r.result?.result?.value;
};

await send("Page.enable");
for (const j of jobs) {
  const width = j.width ?? 1080, height = j.height ?? 1920;
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: j.dpr ?? 2, mobile: false });
  await send("Page.navigate", { url: j.url });
  await sleep(j.loadMs ?? 2500);
  for (const s of j.steps ?? []) { await evaluate(s); await sleep(400); }
  await sleep(j.waitMs ?? 600);
  const params = { format: "png", captureBeyondViewport: !!j.fullPage };
  if (j.fullPage) {
    const h = await evaluate("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)");
    params.clip = { x: 0, y: 0, width, height: h, scale: 1 };
  }
  if (j.clip) params.clip = { x: j.clip.x, y: j.clip.y, width: j.clip.w, height: j.clip.h, scale: 1 };
  const r = await send("Page.captureScreenshot", params);
  mkdirSync(dirname(j.out), { recursive: true });
  writeFileSync(j.out, Buffer.from(r.result.data, "base64"));
  console.log("saved", j.out);
}
ws.close();
proc.kill();
