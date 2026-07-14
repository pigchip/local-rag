import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { streamMessage, type ChatParams } from "@/api/client";
import type { Source, StreamEvent } from "@/api/types";

export interface StreamingState {
  text: string;
  sources: Source[];
  active: boolean;
  error: string | null;
}

const EMPTY: StreamingState = {
  text: "",
  sources: [],
  active: false,
  error: null,
};

export function useChat(sessionId: string | null) {
  const qc = useQueryClient();
  const [streaming, setStreaming] = useState<StreamingState>(EMPTY);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (params: ChatParams) => {
      if (!sessionId) return;
      abortRef.current = new AbortController();
      setStreaming({ text: "", sources: [], active: true, error: null });

      const onEvent = (event: StreamEvent) => {
        if (event.type === "sources") {
          setStreaming((s) => ({ ...s, sources: event.sources }));
        } else if (event.type === "token") {
          setStreaming((s) => ({ ...s, text: s.text + event.text }));
        } else if (event.type === "error") {
          setStreaming((s) => ({ ...s, error: event.error, active: false }));
        } else if (event.type === "done") {
          setStreaming((s) => ({ ...s, active: false }));
        }
      };

      try {
        await streamMessage(sessionId, params, onEvent, abortRef.current.signal);
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setStreaming((s) => ({
            ...s,
            error: (err as Error).message,
            active: false,
          }));
        }
      } finally {
        // Wait for the persisted session to reload before clearing the live
        // streaming bubble, otherwise the answer renders twice (streamed copy +
        // refetched copy) or briefly flickers out. Preserve any error message.
        await qc.invalidateQueries({ queryKey: ["session", sessionId] });
        qc.invalidateQueries({ queryKey: ["sessions"] });
        setStreaming((s) => (s.error ? { ...s, active: false } : EMPTY));
      }
    },
    [sessionId, qc]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStreaming((s) => ({ ...s, active: false }));
  }, []);

  return { streaming, send, stop };
}
