import fs from "fs";
import path from "path";
import crypto from "crypto";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TOKEN_FILE = path.resolve(__dirname, "../.research-approval-token");

let researchApprovalToken;

function loadResearchApprovalToken() {
  if (researchApprovalToken) return researchApprovalToken;

  if (process.env.RESEARCH_APPROVAL_TOKEN) {
    researchApprovalToken = process.env.RESEARCH_APPROVAL_TOKEN;
    return researchApprovalToken;
  }

  try {
    const existing = fs.readFileSync(TOKEN_FILE, "utf8").trim();
    if (existing) {
      researchApprovalToken = existing;
      return researchApprovalToken;
    }
  } catch {}

  const generated = crypto.randomBytes(32).toString("hex");
  try {
    fs.writeFileSync(TOKEN_FILE, generated, { mode: 0o600, flag: "wx" });
    researchApprovalToken = generated;
    console.warn(
      `[research-auth] RESEARCH_APPROVAL_TOKEN is not set; generated persistent token at ${TOKEN_FILE}`
    );
    return researchApprovalToken;
  } catch (err) {
    if (err?.code === "EEXIST") {
      const existing = fs.readFileSync(TOKEN_FILE, "utf8").trim();
      if (existing) {
        researchApprovalToken = existing;
        return researchApprovalToken;
      }
    }
    throw err;
  }
}

export function getResearchApprovalToken() {
  return loadResearchApprovalToken();
}

export function requireResearchAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  const bearerToken = authHeader?.startsWith("Bearer ") ? authHeader.slice(7).trim() : "";
  const headerToken = req.headers["x-research-token"]?.toString().trim() || "";
  const providedToken = bearerToken || headerToken;

  if (!providedToken) {
    return res.status(401).json({ error: "缺少研究部审批令牌" });
  }

  if (providedToken !== loadResearchApprovalToken()) {
    return res.status(401).json({ error: "研究部审批令牌无效" });
  }

  next();
}
