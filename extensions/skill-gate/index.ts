import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { readFileSync } from "node:fs";

// ─── Tool → Required Skill mapping ──────────────────────────────────
// Each key is a native/plugin tool name.
// Value is an array of skill IDs — agent needs ANY ONE of them to pass.
// MCP tools (called via `exec` + `npx mcporter call`) are NOT intercepted
// here because `before_tool_call` only sees the `exec` tool name.
const TOOL_SKILL_GATES: Record<string, string[]> = {
  browser: ["browser-base"],
  // Future:
  // gateway: ["admin-ops"],
};

const EQUIPMENT_PATH = "/home/rooot/.openclaw/dashboard/bot-equipment.json";

type EquipmentData = {
  bots: Record<
    string,
    {
      slots: Record<string, string | null>;
      overflow?: string[];
    }
  >;
};

/**
 * Load bot-equipment.json and build agentId → Set<skillId> mapping.
 * Skills come from both `slots` values and `overflow` array.
 */
function loadEquipment(logger: { warn: (msg: string) => void }): Record<string, Set<string>> {
  const result: Record<string, Set<string>> = {};
  try {
    const raw = readFileSync(EQUIPMENT_PATH, "utf-8");
    const data: EquipmentData = JSON.parse(raw);
    for (const [botId, bot] of Object.entries(data.bots)) {
      const skills = new Set<string>();
      // Collect from slots
      for (const value of Object.values(bot.slots)) {
        if (typeof value === "string" && value) {
          skills.add(value);
        }
      }
      // Collect from overflow
      if (Array.isArray(bot.overflow)) {
        for (const s of bot.overflow) {
          if (typeof s === "string" && s) {
            skills.add(s);
          }
        }
      }
      result[botId] = skills;
    }
  } catch (err) {
    logger.warn(`[skill-gate] Failed to load ${EQUIPMENT_PATH}: ${err}`);
  }
  return result;
}

// ─── Prime Directive ─────────────────────────────────────────────────
// Injected as the FIRST thing every agent sees on every session start.
const SKILL_FIRST = "⚡ Skill-first: check EQUIPPED_SKILLS.md before acting.";

function buildPrimeDirective(): string {
  const now = new Date();
  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const ts = `${weekdays[now.getDay()]} ${months[now.getMonth()]} ${now.getDate()}, ${now.getFullYear()} ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  return `${SKILL_FIRST} | Now: ${ts}`;
}

const skillGatePlugin = {
  id: "skill-gate",
  name: "Skill Gate",
  description: "Block tool calls when the agent lacks the required equipped skill, and inject prime directive",

  register(api: OpenClawPluginApi) {
    const logger = api.logger ?? console;

    // Load equipment data at startup
    let agentSkills = loadEquipment(logger);
    const botCount = Object.keys(agentSkills).length;
    const gatedTools = Object.keys(TOOL_SKILL_GATES).join(", ");
    logger.info?.(`[skill-gate] Loaded equipment for ${botCount} agents. Gated tools: ${gatedTools}`);

    // ── Prime Directive: inject at top of every agent session ──────────
    api.on("before_agent_start", async () => {
      return { prependContext: buildPrimeDirective() };
    }, { priority: 1000 }); // Highest priority — first thing injected

    // ── Tool Gate: block unequipped tool calls ────────────────────────
    api.on(
      "before_tool_call",
      async (event, ctx) => {
        const gates = TOOL_SKILL_GATES[event.toolName];
        if (!gates) return; // Not a gated tool — allow

        const agentId = ctx.agentId;
        if (!agentId) return; // No agent context (CLI?) — allow

        const equipped = agentSkills[agentId];
        if (!equipped) {
          // Agent not in equipment table — reload once in case file was updated
          agentSkills = loadEquipment(logger);
          const reloaded = agentSkills[agentId];
          if (!reloaded) return; // Still not found — allow (unknown agent)
          if (gates.some((skill) => reloaded.has(skill))) return; // Equipped after reload
        } else if (gates.some((skill) => equipped.has(skill))) {
          return; // Equipped — allow
        }

        // Not equipped — block
        return {
          block: true,
          blockReason:
            `Tool '${event.toolName}' requires skill [${gates.join(" or ")}] but your agent '${agentId}' does not have it equipped. ` +
            `Check EQUIPPED_SKILLS.md — if the skill IS listed, Read the corresponding skills/*/SKILL.md first, then retry.`,
        };
      },
      { priority: 100 }, // High priority — run before other hooks
    );
  },
};

export default skillGatePlugin;
