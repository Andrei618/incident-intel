import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import { ticketSchema } from "@/schemas/api/ticket";

export function useTicket(ticketId: string) {
  const {
    data: ticket,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.tickets.detail(ticketId),
    queryFn: () => apiClient.get(`/api/v1/tickets/${ticketId}`, ticketSchema),
    enabled: !!ticketId,
  });
  return { ticket, isLoading, error };
}
