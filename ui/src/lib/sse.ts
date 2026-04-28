import type { SSEEvent } from "@/types/chat";

export async function* parseSSE(
  stream: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop()!;

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const json = part.slice(6);
        const event = JSON.parse(json);
        yield event as SSEEvent;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
