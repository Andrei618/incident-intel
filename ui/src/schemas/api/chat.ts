import { z } from "zod";
import { sourceItemSchema } from "./conversation";

export const chatResponseSchema = z.object({
  conversation_id: z.string(),
  message_id: z.string(),
  answer: z.string(),
  sources: z.array(sourceItemSchema),
  route_used: z.enum(["sql", "hybrid", "clarify"]),
  confidence: z.number().nullable().optional(),
});
