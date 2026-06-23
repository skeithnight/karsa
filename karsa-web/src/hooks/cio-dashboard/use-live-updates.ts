/**
 * WebSocket Live Updates Hook — Sprint-60
 *
 * Connects to /api/cio/ws/live for real-time portfolio updates.
 * Updates TanStack Query cache on every message (no polling delay).
 * Auto-reconnects with exponential backoff on disconnect.
 */
'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface WebSocketMessage {
  type: 'initial_state' | 'portfolio_update' | 'mtm_update' | 'stale_data_alert' | 'heartbeat';
  data?: Record<string, unknown>;
}

interface UseLiveUpdatesOptions {
  enabled?: boolean;
  onStaleDataAlert?: (state: string) => void;
}

export function useLivePortfolioUpdates(options: UseLiveUpdatesOptions = {}) {
  const { enabled = true, onStaleDataAlert } = options;
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const mountedRef = useRef(true);

  const maxReconnectDelay = 30000; // 30 seconds max

  const connect = useCallback(() => {
    if (!enabled || !mountedRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/cio/ws/live`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg: WebSocketMessage = JSON.parse(event.data);

          switch (msg.type) {
            case 'initial_state':
            case 'portfolio_update':
            case 'mtm_update':
              // Update TanStack Query cache directly — instant UI update
              if (msg.data) {
                queryClient.setQueryData(
                  ['cio-dashboard', 'portfolio-summary'],
                  (old: Record<string, unknown> | undefined) => ({
                    ...old,
                    ...msg.data,
                  })
                );
              }
              break;

            case 'stale_data_alert':
              if (msg.data?.state && onStaleDataAlert) {
                onStaleDataAlert(msg.data.state as string);
              }
              // Also update the stale data query cache
              queryClient.setQueryData(
                ['cio-dashboard', 'stale-data'],
                msg.data
              );
              break;

            case 'heartbeat':
              // Connection alive, no action needed
              break;
          }
        } catch {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (mountedRef.current) {
          // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s max
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttemptRef.current),
            maxReconnectDelay
          );
          reconnectAttemptRef.current++;
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror, triggering reconnect
      };
    } catch {
      // WebSocket constructor failed — retry
      if (mountedRef.current) {
        const delay = Math.min(
          1000 * Math.pow(2, reconnectAttemptRef.current),
          maxReconnectDelay
        );
        reconnectAttemptRef.current++;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    }
  }, [enabled, queryClient, onStaleDataAlert]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}
