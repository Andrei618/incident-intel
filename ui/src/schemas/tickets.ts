import { z } from "zod";

export const ticketCreateSchema = z.object({
  title: z.string().min(1, "Title is required").max(255),
  description: z.string().optional(),
  service_id: z.uuid(),
  priority: z.enum(["p1", "p2", "p3", "p4"]),
  assignee: z.string().optional(),
  reporter: z.string().optional(),
});

export type TicketCreate = z.infer<typeof ticketCreateSchema>

export const ticketUpdateSchema = z.
  object({
    title: z.string().min(1, "Title is required").max(255),
    description: z.string().optional(),
    priority: z.enum(["p1", "p2", "p3", "p4"]),
    assignee: z.string().optional(),
    reporter: z.string().optional(),
  })
  .partial();

export type TicketUpdate = z.infer<typeof ticketUpdateSchema>
