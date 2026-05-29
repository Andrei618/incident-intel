import { config } from "@/config";
import { z } from "zod";
import { ApiError, ValidationError } from "./errors";

function isSchema(v: unknown): v is z.ZodType {
  return typeof v === "object" && v !== null && "safeParse" in v;
}
export function request<T>(path: string, init?: RequestInit): Promise<T>;

export function request<S extends z.ZodType>(
  path: string,
  schema: S,
  init?: RequestInit
): Promise<z.infer<S>>;

export async function request(
  path: string,
  schemaOrInit?: z.ZodType | RequestInit,
  maybeInit?: RequestInit
): Promise<unknown> {
  const schema = isSchema(schemaOrInit) ? schemaOrInit : undefined;
  const init = isSchema(schemaOrInit) ? maybeInit : schemaOrInit;
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body, `${res.status} ${res.statusText}`);
  }

  if (res.status === 204) return undefined;

  const body = await res.json();

  if (schema) {
    const result = schema.safeParse(body);
    if (!result.success)
      throw new ValidationError(path, result.error.issues, body);
    return result.data;
  }
  return body;
}

export const apiClient = {
  get: <S extends z.ZodType>(path: string, schema: S) => request(path, schema),
  post: <S extends z.ZodType>(path: string, body: unknown, schema: S) =>
    request(path, schema, { method: "POST", body: JSON.stringify(body) }),
  put: <S extends z.ZodType>(path: string, body: unknown, schema: S) =>
    request(path, schema, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string) =>
    request(path, { method: "DELETE" }),
};
