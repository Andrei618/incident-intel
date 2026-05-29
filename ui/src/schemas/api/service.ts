import { z } from "zod"

export const serviceSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  created_at: z.string(),
})

export const serviceListSchema = z.array(serviceSchema)
