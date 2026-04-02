import fs from "fs";
import path from "path";
import crypto from "crypto";
import { fileURLToPath } from "url";
import jwt from "jsonwebtoken";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const JWT_SECRET_FILE = path.resolve(__dirname, "../.jwt-secret");
const TOKEN_EXPIRY = "24h";
let jwtSecret;

function loadJwtSecret() {
  if (jwtSecret) return jwtSecret;

  if (process.env.JWT_SECRET) {
    jwtSecret = process.env.JWT_SECRET;
    return jwtSecret;
  }

  try {
    const existing = fs.readFileSync(JWT_SECRET_FILE, "utf8").trim();
    if (existing) {
      jwtSecret = existing;
      return jwtSecret;
    }
  } catch {}

  const generated = crypto.randomBytes(32).toString("hex");
  try {
    fs.writeFileSync(JWT_SECRET_FILE, generated, { mode: 0o600, flag: "wx" });
    jwtSecret = generated;
    console.warn(`[auth] JWT_SECRET is not set; generated persistent secret at ${JWT_SECRET_FILE}`);
    return jwtSecret;
  } catch (err) {
    if (err?.code === "EEXIST") {
      const existing = fs.readFileSync(JWT_SECRET_FILE, "utf8").trim();
      if (existing) {
        jwtSecret = existing;
        return jwtSecret;
      }
    }
    throw err;
  }
}

export function signToken(clientId) {
  return jwt.sign({ sub: clientId }, loadJwtSecret(), { expiresIn: TOKEN_EXPIRY });
}

export function verifyToken(token) {
  return jwt.verify(token, loadJwtSecret());
}

// Express middleware: require auth
export function requireAuth(req, res, next) {
  const header = req.headers.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    return res.status(401).json({ error: "未登录" });
  }
  try {
    const payload = verifyToken(header.slice(7));
    req.clientId = payload.sub;
    next();
  } catch {
    return res.status(401).json({ error: "登录已过期" });
  }
}
