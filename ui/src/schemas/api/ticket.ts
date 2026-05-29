import { z } from "zod"

export const ticketSchema = z.object({
  id: z.string(),
  service_id: z.string(),
  title: z.string(),
  description: z.string().nullable(),
  status: z.enum(["open", "in_progress", "resolved", "closed"]),
  priority: z.enum(["p1", "p2", "p3", "p4"]),
  created_at: z.string(),
  started_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  resolved_at: z.string().nullable(),
  closed_at: z.string().nullable(),
  assignee: z.string().nullable(),
  reporter: z.string().nullable(),
})

export const ticketListSchema = z.object({
  items: z.array(ticketSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})
