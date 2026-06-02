import { http, HttpResponse } from "msw";
import type { SourceItem } from "@/types/chat";

interface SSEHandlerOptions {
  tokens?: string[];
  sources?: SourceItem[];
  confidence?: number | null;
}

export function makeChatSSEHandler({
  tokens = ["Hello"],
  sources = [],
  confidence = null,
}: SSEHandlerOptions = {}) {
  return http.post("*/api/v1/chat", () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        for (const token of tokens) {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: "token", content: token })}\n\n`
            )
          );
        }
        const done = {
          type: "done",
          conversation_id: "c1",
          message_id: "m1",
          sources,
          route_used: "hybrid",
          confidence,
        };
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(done)}\n\n`)
        );
        controller.close();
      },
    });
    return new HttpResponse(body, {
      headers: { "Content-Type": "text/event-stream"},
    })
  });
}

export const handlers = [];
