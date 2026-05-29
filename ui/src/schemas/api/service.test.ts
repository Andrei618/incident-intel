import { serviceListSchema } from "./service";

it("parses valid serviceSchema", () => {
  const service = {
    id: "123_abc",
    name: "test service",
    description: null,
    created_at: "2026-05-27T10:00:01Z",
  };
  const serviceList = [service]

  const result = serviceListSchema.safeParse(serviceList);
  expect(result.success).toBe(true);
})

it("parses invalid serviceSchema", () => {
  const service = {
    id: "123_abc",
    name: 1,  // wrong type
    description: null,
    created_at: "2026-05-27T10:00:01Z",
  };
  const serviceList = [service]

  const result = serviceListSchema.safeParse(serviceList);
  expect(result.success).toBe(false);
})
