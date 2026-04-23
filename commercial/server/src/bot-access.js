import { getDb } from "./db.js";
import { verifyToken } from "./auth.js";

export function clientCanAccessBot(db, clientId, botId) {
  const client = db.prepare("SELECT bot_access_mode FROM clients WHERE id = ?").get(clientId);
  if (!client || client.bot_access_mode === "all") return true;
  const row = db.prepare("SELECT 1 FROM client_bot_access WHERE client_id = ? AND bot_id = ?").get(clientId, botId);
  return !!row;
}

export function getClientAllowedBotIds(db, clientId) {
  const client = db.prepare("SELECT bot_access_mode FROM clients WHERE id = ?").get(clientId);
  if (!client || client.bot_access_mode === "all") return null;
  return db.prepare("SELECT bot_id FROM client_bot_access WHERE client_id = ?").all(clientId).map((r) => r.bot_id);
}

export function tryResolveClientId(req) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) return null;
  try {
    const payload = verifyToken(authHeader.slice(7));
    return payload.sub;
  } catch {
    return null;
  }
}
