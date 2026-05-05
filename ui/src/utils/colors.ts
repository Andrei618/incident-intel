import type { components } from "@/types/api";
type TicketStatus = components["schemas"]["TicketStatus"];
type TicketPriority = components["schemas"]["TicketPriority"];

export function statusColor(status: TicketStatus): string {
  switch (status) {
    case "open":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    case "in_progress":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    case "resolved":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "closed":
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  }
}

export function priorityColor(priority: TicketPriority): string {
  switch (priority) {
    case "p1":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
    case "p2":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200";
    case "p3":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    case "p4":
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  }
}
