import { documentListSchema } from "./document";

it("parses valid documentListSchema", () => {
  const document = {
    id: "123_abc",
    service_id: "123_abc",
    title: "test title",
    doc_type: "runbook",
    created_at: "2026-05-27T10:00:01Z",
    updated_at: null,
  };

  const documentList = {
    items: [document],
    total: 100,
    limit: 10,
    offset: 10,
  };
  const result = documentListSchema.safeParse(documentList);
  expect(result.success).toBe(true);
});

it("parses invalid documentListSchema", () => {
  const document = {
    id: "123_abc",
    service_id: "123_abc",
    title: "test title",
    doc_type: "runbook",
    created_at: "2026-05-27T10:00:01Z",
    updated_at: null,
  };

  const documentList = {
    items: [document],
    total: "100",
    limit: 10,
    offset: 10,
  };
  const result = documentListSchema.safeParse(documentList);
  expect(result.success).toBe(false);
});