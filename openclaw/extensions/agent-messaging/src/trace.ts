import type { TraceEntry } from "./types.js";

export type RouteDecision =
  | {
      kind: "wake_agent";
      agent: string;
      session_id?: string;
    }
  | {
      kind: "deliver_external";
      agent: string;
      session_id?: string;
      reply_channel: string;
      reply_to: string;
      reply_account: string;
    };

/**
 * Route a reply to the previous hop in the trace chain.
 * Always wakes the agent — even if it's the origin with reply_channel.
 * The origin agent can then decide whether to forward to the user.
 */
export function resolveReplyRoute(trace: TraceEntry[]): RouteDecision {
  if (trace.length === 0) {
    throw new Error("Cannot resolve reply route: trace is empty");
  }

  const last = trace[trace.length - 1];

  return {
    kind: "wake_agent",
    agent: last.agent,
    session_id: last.session_id,
  };
}

/**
 * Find the origin entry (first entry with reply_channel) and deliver directly
 * to the external user, skipping all intermediate agents.
 */
export function resolveDirectDeliveryRoute(trace: TraceEntry[]): RouteDecision | null {
  for (const entry of trace) {
    if (entry.reply_channel && entry.reply_to) {
      // Fall back to entry.agent if reply_account was omitted
      const account = entry.reply_account || entry.agent;
      return {
        kind: "deliver_external",
        agent: entry.agent,
        session_id: entry.session_id,
        reply_channel: entry.reply_channel,
        reply_to: entry.reply_to,
        reply_account: account,
      };
    }
  }
  return null;
}

/**
 * Pop the last trace entry (used when peeling back one hop on reply).
 * Returns a new array without the last entry.
 */
export function popTrace(trace: TraceEntry[]): TraceEntry[] {
  if (trace.length <= 1) return [];
  return trace.slice(0, -1);
}
