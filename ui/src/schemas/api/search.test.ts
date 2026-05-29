import { searchResponseSchema } from "./search";

it("parses valid searchResponseSchema", () => {
  const searchItem = {
    chunk_id: "123_abc",
    document_id: "123_abc",
    document_title: "test document",
    content: "test content",
    chunk_index: 1,
    score: 0.9,
  };

  const searchItemList = {
    items: [searchItem],
    query: "test query",
    total: 10,
    method: "keyword",
  };
  const result = searchResponseSchema.safeParse(searchItemList);
  expect(result.success).toBe(true);
});

it("parses invalid searchResponseSchema", () => {
  const searchItem = {
    chunk_id: "123_abc",
    document_id: "123_abc",
    document_title: "test document",
    content: "test content",
    chunk_index: "1",  // wrong type
    score: 0.9,
  };

  const searchItemList = {
    items: [searchItem],
    query: "test query",
    total: 10,
    method: "keyword",
  };
  const result = searchResponseSchema.safeParse(searchItemList);
  expect(result.success).toBe(false);
});
