import { ticketListSchema } from "./ticket";

it("parses valid ticketListSchema", () => {
  const ticket = {
    id: "123_abc",
    service_id: "123_abc",
    title: "test title",
    description: null,
    status: "open",
    priority: "p1",
    created_at: "2026-05-27T10:00:01Z",
    started_at: null,
    updated_at: null,
    resolved_at: null,
    closed_at: null,
    assignee: "test assignee",
    reporter: null,
  };

  const ticketList = {
    items: [ticket],
    total: 100,
    limit: 10,
    offset: 10,
  };
  const result = ticketListSchema.safeParse(ticketList);
  expect(result.success).toBe(true);
});

it("parses invalid ticketListSchema", () => {
  const ticket = {
    id: "123_abc",
    service_id: "123_abc",
    title: "test title",
    description: 0,  // wrong type
    status: "open",
    priority: "p1",
    created_at: "2026-05-27T10:00:01Z",
    started_at: null,
    updated_at: null,
    resolved_at: null,
    closed_at: null,
    assignee: "test assignee",
    reporter: null,
  };

  const ticketList = {
    items: [ticket],
    total: 100,
    limit: 10,
    offset: 10,
  };
  const result = ticketListSchema.safeParse(ticketList);
  expect(result.success).toBe(false);
});