import { Router } from "express";
import bcrypt from "bcryptjs";
import { getDb } from "../db.js";
import { signToken, requireAuth } from "../auth.js";

const router = Router();

// POST /api/auth/register
router.post("/register", (req, res) => {
  const { username, password, display_name, company, phone } = req.body;
  if (!username || !password || !display_name) {
    return res.status(400).json({ error: "用户名、密码、昵称为必填项" });
  }
  if (password.length < 6) {
    return res.status(400).json({ error: "密码至少6位" });
  }

  const db = getDb();
  const existing = db.prepare("SELECT id FROM clients WHERE username = ?").get(username);
  if (existing) {
    return res.status(409).json({ error: "用户名已存在" });
  }

  const hash = bcrypt.hashSync(password, 10);
  const result = db.prepare(
    "INSERT INTO clients (username, password_hash, display_name, company, phone) VALUES (?, ?, ?, ?, ?)"
  ).run(username, hash, display_name, company || "", phone || "");

  const token = signToken(result.lastInsertRowid);
  res.status(201).json({
    token,
    client: { id: result.lastInsertRowid, username, display_name, company: company || "" },
  });
});

// POST /api/auth/login
router.post("/login", (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.status(400).json({ error: "请输入用户名和密码" });
  }

  const db = getDb();
  const client = db.prepare("SELECT * FROM clients WHERE username = ?").get(username);
  if (!client || !bcrypt.compareSync(password, client.password_hash)) {
    return res.status(401).json({ error: "用户名或密码错误" });
  }
  if (client.status !== "active") {
    return res.status(403).json({ error: "账户已被停用" });
  }

  const token = signToken(client.id);
  res.json({
    token,
    client: { id: client.id, username: client.username, display_name: client.display_name, company: client.company },
  });
});

// GET /api/auth/me
router.get("/me", requireAuth, (req, res) => {
  const db = getDb();
  const client = db.prepare("SELECT id, username, display_name, company, phone, created_at FROM clients WHERE id = ?").get(req.clientId);
  if (!client) return res.status(404).json({ error: "用户不存在" });
  res.json(client);
});

export default router;
