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
import { ensureBotCatalog } from "./services/bot-catalog.js";

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

app.listen(PORT, () => {
  console.log(`Commercial Order System running on :${PORT}`);
});
