import type { components } from "@/types/api";
type TicketStatus = components["schemas"]["TicketStatus"];
type TicketPriority = components["schemas"]["TicketPriority"];
type DocType = components["schemas"]["DocType"];

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
  }
}

export function docTypeColor(docType: DocType): string {
  switch (docType) {
    case "runbook":
      return "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200";
    case "policy":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
    case "guide":
      return "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200";
    case "faq":
      return "bg-slate-100 text-slate-800 dark:bg-slate-900 dark:text-slate-200";
  }
}
