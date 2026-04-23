import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 本地开发可设 env 指向真实 .openclaw/；云端不设则用 deps/
export const OPENCLAW_DIR = process.env.OPENCLAW_DIR
  || path.resolve(__dirname, "../../deps");
