import express from "express";
import cors from "cors";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { getDb } from "./db.js";
import authRoutes from "./routes/auth.js";
import botsRoutes from "./routes/bots.js";
import ordersRoutes from "./routes/orders.js";
import draftsRoutes from "./routes/drafts.js";
import uploadsRoutes from "./routes/uploads.js";
import publishRoutes from "./routes/publish.js";
import researchRoutes from "./routes/research.js";
import adminRoutes from "./routes/admin.js";
import consultRoutes from "./routes/consult.js";
import { ensureBotCatalog } from "./services/bot-catalog.js";
import { reconcilePublishingOrders } from "./services/publish-bridge.js";
import { seedWhitelistAccounts } from "./services/whitelist-seed.js";
import { sweepStaleArtifacts } from "./services/order-cleanup.js";
import { attachToExpress as attachTunnel } from "./tunnel/server.js";

// Force stdio to blocking (synchronous) writes — when commercial is launched
// via nohup and redirected to /tmp/commercial-18900.log, Node's default async
// piped-file mode block-buffers logs, which hides live diagnostics. Blocking
// writes make every console.log/error land on disk immediately.
try {
  if (process.stdout._handle?.setBlocking) process.stdout._handle.setBlocking(true);
  if (process.stderr._handle?.setBlocking) process.stderr._handle.setBlocking(true);
} catch {}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.PORT || "18900");

const app = express();

app.use(cors());
app.use(express.json({ limit: "2mb" }));

// Health check
app.get("/api/health", (req, res) => {
  const db = getDb();
  const orderCount = db.prepare("SELECT COUNT(*) as count FROM orders").get();
  res.json({
    status: "ok",
    uptime: process.uptime(),
    activeOrders: orderCount.count,
  });
});

// API routes
app.use("/api/auth", authRoutes);
app.use("/api/bots", botsRoutes);
app.use("/api/orders", ordersRoutes);
app.use("/api/orders", draftsRoutes);
app.use("/api/orders", uploadsRoutes);
app.use("/api/orders", publishRoutes);
app.use("/api/research", researchRoutes);
app.use("/api/admin", adminRoutes);
app.use("/api/consult", consultRoutes);

// Serve Vue SPA in production
const clientDist = path.resolve(__dirname, "../../client/dist");
const clientIndex = path.join(clientDist, "index.html");
app.use(express.static(clientDist));
app.get(/^\/(?!api).*/, (req, res) => {
  try {
    res.type("html").send(fs.readFileSync(clientIndex, "utf8"));
  } catch {
    res.status(404).json({ error: "前端未构建" });
  }
});

// Init DB and sync bot catalog on startup
getDb();
ensureBotCatalog();
seedWhitelistAccounts();

// Reconcile orders stuck in `publishing` once on boot, then every 60s.
// Handles dashboard "打回" / sys1 moves that commercial otherwise can't see.
// Also piggybacks a safety-net sweep of iteration scratch for any order that
// has silently reached a terminal state without going through the usual hooks.
async function safeReconcile() {
  try {
    const n = await reconcilePublishingOrders();
    if (n > 0) console.log(`[boot] Reconciled ${n} publishing order(s)`);
  } catch (err) {
    console.error("[boot] Reconcile failed:", err);
  }
  try {
    const n = await sweepStaleArtifacts();
    if (n > 0) console.log(`[boot] Swept ${n} stale artifact(s)`);
  } catch (err) {
    console.error("[boot] Sweep failed:", err);
  }
}
safeReconcile();
setInterval(() => safeReconcile().catch(() => {}), 60 * 1000);

attachTunnel(app);
app.listen(PORT, () => {
  console.log(`Commercial Order System running on :${PORT}`);
});
