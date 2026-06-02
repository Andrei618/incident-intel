import { chatResponseSchema } from "./chat";

it("parses valid chatResponseSchema", () => {
  const sourceItem = {
    chunk_id: "123_abc",
    document_id: "012_klm",
    document_title: "test document",
    chunk_index: 1,
    relevance_score: 0.9,
  };
  const chatResponse = {
    conversation_id: "123_abc",
    message_id: "123_abc",
    answer: "test answer",
    sources: [sourceItem],
    route_used: "sql",
    confidence: 0.9,
  };
  const result = chatResponseSchema.safeParse(chatResponse);
  expect(result.success).toBe(true);
});

it("parses invalid chatResponseSchema", () => {
  const sourceItem = {
    chunk_id: "123_abc",
    document_id: "012_klm",
    document_title: "test document",
    chunk_index: "1",  // wrong type
    relevance_score: 0.9,
  };
  const chatResponse = {
    conversation_id: "123_abc",
    message_id: "123_abc",
    answer: "test answer",
    sources: [sourceItem],
    route_used: "sql",
    confidence: 0.9,
  };
  const result = chatResponseSchema.safeParse(chatResponse);
  expect(result.success).toBe(false);
});
