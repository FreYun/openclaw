import { Router } from "express";
import bcrypt from "bcryptjs";
import { getDb } from "../db.js";
import { signToken, requireAuth } from "../auth.js";

const router = Router();

// POST /api/auth/register — 公开注册已关闭。账号通过 white_id.json 白名单
// 批量 seed,需要开通账号时联系管理员。
router.post("/register", (req, res) => {
  return res.status(403).json({ error: "暂不开放公开注册,如需账号请联系管理员" });
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
    client: { id: client.id, username: client.username, display_name: client.display_name, company: client.company, role: client.role || "client", sys_prompt: client.sys_prompt || "" },
  });
});

// GET /api/auth/me
router.get("/me", requireAuth, (req, res) => {
  const db = getDb();
  const client = db.prepare("SELECT id, username, display_name, company, phone, role, sys_prompt, created_at FROM clients WHERE id = ?").get(req.clientId);
  if (!client) return res.status(404).json({ error: "用户不存在" });
  res.json(client);
});

// PATCH /api/auth/me — update client profile (sys_prompt etc.)
router.patch("/me", requireAuth, (req, res) => {
  const db = getDb();
  const body = req.body || {};
  const updates = [];
  const params = [];

  if (typeof body.sys_prompt === "string") {
    if (body.sys_prompt.length > 5000) return res.status(400).json({ error: "系统提示词过长" });
    updates.push("sys_prompt = ?");
    params.push(body.sys_prompt);
  }

  if (updates.length === 0) return res.status(400).json({ error: "没有可更新字段" });

  updates.push("updated_at = datetime('now')");
  params.push(req.clientId);
  db.prepare(`UPDATE clients SET ${updates.join(", ")} WHERE id = ?`).run(...params);

  const client = db.prepare("SELECT id, username, display_name, company, phone, role, sys_prompt, created_at FROM clients WHERE id = ?").get(req.clientId);
  res.json(client);
});

export default router;
