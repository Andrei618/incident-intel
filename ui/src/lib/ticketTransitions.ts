import type { components } from "@/types/api";

type TicketStatus = components["schemas"]["TicketStatus"]

export const TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  open: ["in_progress", "closed" ],
  in_progress: ["resolved", "open"],
  resolved: ["closed", "in_progress"],
  closed: [],
}

export const TRANSITION_LABELS: Record<TicketStatus, string> = {
  "in_progress": "Start work",
  "resolved": "Mark fixed", 
  "closed": 	"Close",
  "open": 	"Reopen",
}

export function nextStates(status: TicketStatus): TicketStatus[] {
  return (
    TRANSITIONS[status]
  )
}
