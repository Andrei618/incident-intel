import { useState, useRef } from "react";
import { parseSSE } from "./sse";
import type { SourceItem } from "@/types/chat";
import { config } from "@/config";

export function useChatStream() {
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thinkingMs, setThinkingMs] = useState(0);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const controllerRef = useRef<AbortController | null>(null);

  async function submit(message: string) {
    const controller = new AbortController();
    controllerRef.current = controller;

    // reset state
    setAnswer("");
    setSources([]);
    setError(null);
    setIsStreaming(true);
    setThinkingMs(0);

    // start thinking timer — every 100ms add 100ms
    const timer = setInterval(() => setThinkingMs((prev) => prev + 100), 100);

    // fetch and stream loop + handle 3 types of errors
    try {
      const response = await fetch(`${config.apiBaseUrl}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          stream: true,
          options: { limit: 5, include_sources: true },
        }),
        signal: controller.signal,
      });

      // HTTP error before stream starts
      if (!response.ok) {
        setError(`Request failed: ${response.status}`);
        return;
      }

      // Server-side failure during streaming
      let receivedTerminal = false;
      for await (const event of parseSSE(response.body!)) {
        if (event.type === "token") {
          setAnswer((prev) => prev + event.content);
        } else if (event.type === "done") {
          setConversationId(event.conversation_id);
          setSources(event.sources);
          receivedTerminal = true;
        }
        // Server-side failure during streaming
        else if (event.type === "error") {
          setError(event.message);
          receivedTerminal = true;
        }
      }
      
      // Incomplete response
      if (!receivedTerminal) {
        setError("Response incomplete");
      }
    } catch (e) {
      // only set error if it's NOT an AbortError
      if (e instanceof Error && e.name !== "AbortError") {
        setError(e.message);
      }
    } finally {
      clearInterval(timer);
      setIsStreaming(false);
    }
  }
  function abort() {
    controllerRef.current?.abort();
  }
  return { answer, sources, isStreaming, error, thinkingMs, submit, abort };
}
