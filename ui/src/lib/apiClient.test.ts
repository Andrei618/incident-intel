import { http, HttpResponse } from "msw";
import { z } from "zod";
import { server } from "@/test/mocks/server";
import { apiClient, request } from "./apiClient";
import { ApiError, ValidationError } from "./errors";

it("returns parsed JSON on 200", async () => {
  server.use(http.get("*/test", () => HttpResponse.json({ ok: true })));
  const result = await request("/test");
  expect(result).toEqual({ ok: true });
});

it("throws ApiError on 404", async () => {
  server.use(http.get("*/test", () => new HttpResponse(null, { status: 404 })));
  await expect(request("/test")).rejects.toThrow(ApiError);
});

it("returns schema-validated data when response matches", async () => {
  server.use(http.get("*/test", () => HttpResponse.json({ ok: true })));
  const schema = z.object({ ok: z.boolean() });
  const result = await apiClient.get("/test", schema);
  expect(result).toEqual({ ok: true });
});

it("throws ValidationError when response doesn't match schema", async () => {
  server.use(http.get("*/test", () => HttpResponse.json({ ok: true })));
  const schema = z.object({ ok: z.string() });
  await expect(apiClient.get("/test", schema)).rejects.toThrow(ValidationError);
});
