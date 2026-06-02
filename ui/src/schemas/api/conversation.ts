import { z } from "zod";

export const sourceItemSchema = z.object({
  chunk_id: z.string(),
  document_id: z.string(),
  document_title: z.string(),
  chunk_index: z.number(),
  relevance_score: z.number(),
});

export const messageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  created_at: z.string(),
  sources: z.array(sourceItemSchema),
});

export const conversationSchema = z.object({
  id: z.string(),
  created_at: z.string(),
});

export const conversationDetailSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  messages: z.array(messageSchema),
});

export const conversationListSchema = z.object({
  items: z.array(conversationSchema),
  total: z.number(),
});
