import { z } from "zod"

const envSchema = z.object({
  VITE_API_BASE_URL: z.url(),
});

const env = envSchema.parse(import.meta.env)

export const config = {
  apiBaseUrl: env.VITE_API_BASE_URL,
} as const;
