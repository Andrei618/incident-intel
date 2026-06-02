import { z } from "zod";

export const searchResultItemSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string(),
  document_title: z.string(),
  content: z.string(),
  chunk_index: z.number(),
  score: z.number(),
});

export const searchResponseSchema = z.object({
  items: z.array(searchResultItemSchema),
  query: z.string(),
  total: z.number(),
  method: z.enum(["keyword", "vector", "hybrid"]),
});
