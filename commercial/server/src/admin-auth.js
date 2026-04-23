import { getDb } from "./db.js";
import { verifyToken } from "./auth.js";
import { getResearchApprovalToken } from "./research-auth.js";

export function requireAdminAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  const bearerToken = authHeader?.startsWith("Bearer ") ? authHeader.slice(7).trim() : "";
  const headerToken = req.headers["x-research-token"]?.toString().trim() || "";
  const providedToken = bearerToken || headerToken;

  if (!providedToken) {
    return res.status(401).json({ error: "未授权访问" });
  }

  if (providedToken === getResearchApprovalToken()) {
    return next();
  }

  try {
    const payload = verifyToken(bearerToken);
    const db = getDb();
    const client = db.prepare("SELECT id, role FROM clients WHERE id = ?").get(payload.sub);
    if (client && client.role === "admin") {
      req.clientId = client.id;
      return next();
    }
  } catch {}

  return res.status(403).json({ error: "需要管理员权限" });
}
