import { renderHook, act, waitFor } from "@testing-library/react";
import { useChatStream } from "./useChatStream";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";

it("accumulates tokens and sets sources on done", async () => {
  server.use(
    http.post("*/api/v1/chat", () => {
      const encoder = new TextEncoder();
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode('data: {"type":"token","content":"Hello"}\n\n')
          );
          const done = {
            type: "done",
            conversation_id: "c1",
            message_id: "m1",
            sources: [],
            route_used: "hybrid",
            confidence: null,
          };
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(done)}\n\n`)
          );
          controller.close();
        },
      });
      return new HttpResponse(body, {
        headers: { "Content-Type": "text/event-stream" },
      });
    })
  );

  const { result } = renderHook(() => useChatStream());
  act(() => {
    result.current.submit("test");
  });
  await waitFor(() => expect(result.current.isStreaming).toBe(false));
  expect(result.current.answer).toBe("Hello");
  expect(result.current.error).toBeNull();
  expect(result.current.sources).toEqual([]);
});

it("receives HTTP error if no response", async () => {
  server.use(
    http.post("*/api/v1/chat", () => {
      return new HttpResponse(null, { status: 500 });
    })
  );
  const { result } = renderHook(() => useChatStream());
  act(() => {
    result.current.submit("test");
  });
  await waitFor(() => expect(result.current.isStreaming).toBe(false));
  expect(result.current.answer).toBe("");
  expect(result.current.error).toBe("Request failed: 500");
  expect(result.current.isStreaming).toBe(false);
});

it("it receives SSE error if strream sends an error event", async () => {
  server.use(
    http.post("*/api/v1/chat", () => {
      const encoder = new TextEncoder();
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode('data: {"type":"error","message":"LLM failed"}\n\n')
          );
          controller.close();
        },
      });
      return new HttpResponse(body, {
        headers: { "Content-type": "text/event-stream" },
      });
    })
  );

  const { result } = renderHook(() => useChatStream());
  act(() => {
    result.current.submit("test");
  });
  await waitFor(() => expect(result.current.isStreaming).toBe(false));
  expect(result.current.answer).toBe("");
  expect(result.current.error).toBe("LLM failed"); // ??
  expect(result.current.sources).toEqual([]);
});

it("it receives error on missing done event in stream", async () => {
  server.use(
    http.post("*/api/v1/chat", () => {
      const encoder = new TextEncoder();
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode('data: {"type":"token","content":"Hi"}\n\n')
          );
          controller.close();
        },
      });
      return new HttpResponse(body, {
        headers: { "Content-Type": "text/event-stream" },
      });
    })
  );
  const { result } = renderHook(() => useChatStream());
  act(() => {
    result.current.submit("test");
  })
  await waitFor(() => expect(result.current.isStreaming).toBe(false));
  expect(result.current.answer).toBe("Hi");
  expect(result.current.error).toBe("Response incomplete");
  expect(result.current.sources).toEqual([]);
});
