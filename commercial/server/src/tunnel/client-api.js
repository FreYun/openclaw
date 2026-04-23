/**
 * Tunnel Client API — thin import for business code.
 *
 * Usage:
 *   import * as tunnel from "../tunnel/client-api.js";
 *   if (tunnel.isConnected()) { ... }
 *
 * Re-exports the public surface of tunnel/server.js.
 */
export { isConnected, exec, tunnelFetch, readFile, tailFile } from "./server.js";
