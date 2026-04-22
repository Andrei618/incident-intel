import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { apiClient, ApiError } from "./apiClient";

it("returns parsed JSON on 200", async () => {
  server.use(http.get("*/test", () => HttpResponse.json({ ok: true })));
  const result = await apiClient.get<{ ok: boolean }>("/test");
  expect(result.ok).toBe(true);
});

it("throws ApiError on 404", async () => {
  server.use(http.get("*/test", () => new HttpResponse(null, { status: 404 })));
  await expect(apiClient.get("/test")).rejects.toThrow(ApiError);
});
