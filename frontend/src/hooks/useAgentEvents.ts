import { useEffect, useRef, useState, useCallback } from "react";

export interface AgentEvent {
  agentId: string;
  type:
    | "agent_start"
    | "turn_start"
    | "tool_call"
    | "tool_result"
    | "thinking"
    | "assistant_text"
    | "nudge"
    | "done"
    | "ping";
  data: Record<string, unknown>;
  timestamp: number;
}

/**
 * Connect to an agent's WebSocket and stream live events.
 * Returns the event log and connection status.
 */
export function useAgentEvents(agentId: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!agentId) return;

    // Build WebSocket URL (relative in dev via Vite proxy)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const base = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : window.location.host;
    const url = `${protocol}//${base}/api/agents/${agentId}/ws`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (ev) => {
      try {
        const event: AgentEvent = JSON.parse(ev.data);
        if (event.type === "ping") return; // ignore keepalives
        setEvents((prev) => [...prev, event]);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 2s if the agent might still be running
      reconnectTimer.current = setTimeout(() => {
        connect();
      }, 2000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [agentId]);

  useEffect(() => {
    setEvents([]);
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
