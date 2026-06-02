import { z } from "zod";

export const documentSchema = z.object({
  id: z.string(),
  service_id: z.string().nullable(),
  title: z.string(),
  doc_type: z.enum(["runbook", "policy", "guide", "faq"]),
  created_at: z.string(),
  updated_at: z.string().nullable(),
})

export const documentDetailSchema = documentSchema.extend({
  content: z.string(),
})

export const documentListSchema = z.object({
  items: z.array(documentSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})
