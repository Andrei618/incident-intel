/**
 * Toast policy: fire on mutations only (success + error). Query failures use inline error UI.
 * Message format: user-facing strings only — never `error.message` (leaks server detail).
 * Dev signal: pair toast.error(...) with console.error(...) to preserve stack trace.
 * Import path: always from "@/lib/toast", never directly from "sonner".
 */
export { toast } from "sonner"