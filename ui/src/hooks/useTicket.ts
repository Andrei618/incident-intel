import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/apiClient"
import { queryKey } from "@/lib/queryKeys"
import type { components } from "@/types/api"

type TicketResponse = components["schemas"]["TicketResponse"]

export function useTicket(ticketId: string) {
  const { data: ticket, isLoading, error } = useQuery({
    queryKey: queryKey.tickets.detail(ticketId),
    queryFn: () => apiClient.get<TicketResponse>(`/api/v1/tickets/${ticketId}`),
    enabled: !!ticketId
  })
  return { ticket, isLoading, error }
}