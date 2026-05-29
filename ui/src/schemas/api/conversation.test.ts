import { conversationDetailSchema } from "./conversation";

it("parses valid conversationDetailSchema", () => {
  const sourceItem = {
    chunk_id: "123_abc",
    document_id: "012_klm",
    document_title: "test document",
    chunk_index: 1,
    relevance_score: 0.9,
  };
  const message = {
    id: "456_def",
    role: "user",
    content: "test content",
    created_at: "2026-05-27T10:00:01Z",
    sources: [sourceItem],
  };
  const schema = {
    id: "789_hij",
    created_at: "2026-05-27T10:00:02Z",
    messages: [message],
  };
  const result = conversationDetailSchema.safeParse(schema);
  expect(result.success).toBe(true);
});

it("parses invalid conversationDetailSchema", () => {
  const sourceItem = {
    chunk_id: "123_abc",
    document_id: "012_klm",
    document_title: "test document",
    chunk_index: "1",  // wrong type
    relevance_score: 0.9,
  };
  const message = {
    id: "456_def",
    role: "user",
    content: "test content",
    created_at: "2026-05-27T10:00:01Z",
    sources: [sourceItem],
  };
  const schema = {
    id: "789_hij",
    created_at: "2026-05-27T10:00:02Z",
    messages: [message],
  };
  const result = conversationDetailSchema.safeParse(schema);
  expect(result.success).toBe(false);
});
