#!/usr/bin/env node
/**
 * XHS Post Performance Stats Collector
 *
 * Scans published posts from the last 7 days to determine which bots to query,
 * then calls XHS MCP `list_notes` for each bot to fetch performance metrics.
 * Results are saved to xhs-stats.json for the dashboard to display.
 *
 * Usage: node collect-xhs-stats.js
 * Scheduled: crontab every day at 9:00 and 21:00
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

const MCP_PORT = 18060;
const MCP_HOST = "localhost";
const PUBLISH_DIR = path.join(__dirname, "..", "workspace-sys1", "publish-queue", "published");
// Note: workspace-sys1 is the correct path (renamed from workspace-mcp-publisher)
const STATS_FILE = path.join(__dirname, "xhs-stats.json");
const BOT_TIMEOUT = 60000; // 60s per bot
const DELAY_BETWEEN_BOTS = 2000; // 2s

function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

// Find bots that published in the last 7 days
function getRecentPublishingBots() {
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const cutoff = sevenDaysAgo.toISOString().slice(0, 10).replace(/-/g, "-");

  const bots = new Set();
  try {
    const entries = fs.readdirSync(PUBLISH_DIR);
    for (const entry of entries) {
      // Extract date and bot from filename like 2026-03-27T14-38-31_bot7_bjq77j
      const dateMatch = entry.match(/^(\d{4}-\d{2}-\d{2})T/);
      const botMatch = entry.match(/_(\w+?)_/);
      if (dateMatch && botMatch) {
        const date = dateMatch[1];
        if (date >= cutoff) {
          bots.add(botMatch[1]);
        }
      }
    }
  } catch (e) {
    log(`Error reading publish directory: ${e.message}`);
  }
  return [...bots].sort((a, b) => {
    const na = a.match(/^bot(\d+)$/), nb = b.match(/^bot(\d+)$/);
    if (na && nb) return parseInt(na[1]) - parseInt(nb[1]);
    return a.localeCompare(b);
  });
}

// Make an HTTP POST request, return { headers, body }
function httpPost(path, body, headers = {}, timeout = BOT_TIMEOUT) {
  return new Promise((resolve, reject) => {
    const req = http.request({
      hostname: MCP_HOST,
      port: MCP_PORT,
      path,
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json, text/event-stream", ...headers },
      timeout,
    }, (res) => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => resolve({ headers: res.headers, body: data, statusCode: res.statusCode }));
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("timeout")); });
    req.write(JSON.stringify(body));
    req.end();
  });
}

// Initialize MCP session for a bot, returns session ID or null
async function mcpInitialize(botId) {
  try {
    const res = await httpPost(`/mcp/${botId}`, {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "stats-collector", version: "1.0" },
      },
    }, {}, 15000); // 15s timeout for init

    const sessionId = res.headers["mcp-session-id"];
    if (!sessionId) {
      log(`  [${botId}] No session ID in response (status ${res.statusCode})`);
      return null;
    }
    return sessionId;
  } catch (e) {
    log(`  [${botId}] Initialize failed: ${e.message}`);
    return null;
  }
}

// Call list_notes for a bot
async function callListNotes(botId, sessionId) {
  const res = await httpPost(`/mcp/${botId}`, {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/call",
    params: {
      name: "list_notes",
      arguments: {},
    },
  }, { "Mcp-Session-Id": sessionId });

  const jsonRpc = JSON.parse(res.body);
  if (jsonRpc.error) {
    throw new Error(jsonRpc.error.message || JSON.stringify(jsonRpc.error));
  }

  const result = jsonRpc.result;
  if (!result || !result.content || !result.content.length) {
    throw new Error("Empty response");
  }

  // Check for error flag
  if (result.isError) {
    throw new Error(result.content[0].text || "MCP tool error");
  }

  const text = result.content[0].text;
  return JSON.parse(text);
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
  log("=== XHS Stats Collection Start ===");

  // Load existing stats for incremental update
  let existing = { updated_at: null, bots: {} };
  try {
    existing = JSON.parse(fs.readFileSync(STATS_FILE, "utf8"));
  } catch {}

  // Find bots to query
  const bots = getRecentPublishingBots();
  log(`Bots with posts in last 7 days: ${bots.join(", ") || "none"}`);

  if (bots.length === 0) {
    log("No bots to query. Exiting.");
    return;
  }

  const stats = { ...existing, updated_at: new Date().toISOString() };
  let successCount = 0;
  let skipCount = 0;

  for (let i = 0; i < bots.length; i++) {
    const bot = bots[i];
    if (i > 0) await sleep(DELAY_BETWEEN_BOTS);

    log(`Processing ${bot} (${i + 1}/${bots.length})...`);

    // Try to initialize MCP session
    const sessionId = await mcpInitialize(bot);
    if (!sessionId) {
      log(`  [${bot}] Skipped (not logged in or MCP unavailable)`);
      skipCount++;
      continue;
    }

    try {
      const notes = await callListNotes(bot, sessionId);
      const hasNotes = Array.isArray(notes) && notes.length > 0;
      stats.bots[bot] = {
        updated_at: new Date().toISOString(),
        notes: hasNotes ? notes : [],
        error: null,
        loginStatus: { creator: hasNotes },
      };
      log(`  [${bot}] OK - ${hasNotes ? notes.length : 0} notes (creator: ${hasNotes ? "✅" : "❌"})`);
      successCount++;
    } catch (e) {
      log(`  [${bot}] Error: ${e.message}`);
      if (!stats.bots[bot]) {
        stats.bots[bot] = { updated_at: null, notes: [], error: e.message, loginStatus: { creator: false } };
      } else {
        stats.bots[bot].error = e.message;
        stats.bots[bot].loginStatus = { creator: false };
      }
    }
  }

  // Write results
  fs.writeFileSync(STATS_FILE, JSON.stringify(stats, null, 2));
  log(`Done. Success: ${successCount}, Skipped: ${skipCount}, File: ${STATS_FILE}`);
  log("=== XHS Stats Collection End ===");
}

main().catch(e => {
  log(`Fatal error: ${e.message}`);
  process.exit(1);
});
