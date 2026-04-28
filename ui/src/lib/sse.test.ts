import type { SSEEvent } from "@/types/chat";
import { parseSSE } from "./sse";

// helper function
export function makeStream(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        const encoded = encoder.encode(chunk);
        controller.enqueue(encoded);
      }
      controller.close();
    },
  });
}

it("yields a TokenEvent from a single complete frame", async () => {
  const stream = makeStream('data: {"type": "token", "content": "Hello"}\n\n');
  const events: SSEEvent[] = [];

  for await (const event of parseSSE(stream)) {
    events.push(event);
  }

  expect(events).toHaveLength(1);
  expect(events[0]).toEqual({ type: "token", content: "Hello" });
});

it("yields two events from two complete frames", async () => {
  const stream = makeStream(
    'data: {"type": "token", "content": "Hello"}\n\ndata: {"type": "error", "message": "error message"}\n\n'
  );
  const events: SSEEvent[] = [];

  for await (const event of parseSSE(stream)) {
    events.push(event);
  }

  expect(events).toHaveLength(2);
  expect(events[0]).toEqual({ type: "token", content: "Hello" });
  expect(events[1]).toEqual({ type: "error", message: "error message" });
});

it("yields one event from one frame splitted across two makeStream arguments", async () => {
  const stream = makeStream('data: {"type":"token","cont', 'ent":"Hello"}\n\n');
  const events: SSEEvent[] = [];

  for await (const event of parseSSE(stream)) {
    events.push(event);
  }

  expect(events).toHaveLength(1);
  expect(events[0]).toEqual({ type: "token", content: "Hello" });
});

it("yileds nothing from lines without data: prefix", async () => {
  const stream = makeStream(": keep-alive\n\n");
  const events: SSEEvent[] = [];

  for await (const event of parseSSE(stream)) {
    events.push(event);
  }

  expect(events).toHaveLength(0);
});

it("yields a DoneEvent with sources", async () => {
  const doneEvent = {
    type: "done",
    conversation_id: "abc",
    message_id: "xyz",
    sources: [
      {
        chunk_id: "1",
        document_id: "2",
        document_title: "Doc",
        chunk_index: 0,
        relevance_score: 0.9,
      },
    ],
    route_used: "hybrid",
    confidence: null,
  };
  const stream = makeStream(`data: ${JSON.stringify(doneEvent)}\n\n`);
  const events: SSEEvent[] = [];

  for await (const event of parseSSE(stream)) {
    events.push(event);
  }

  expect(events).toHaveLength(1);
  expect(events[0]).toEqual(doneEvent);
});
