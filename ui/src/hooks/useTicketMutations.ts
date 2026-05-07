import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { queryKey } from "@/lib/queryKeys";
import { apiClient } from "@/lib/apiClient";
import type { components } from "@/types/api";
import type { TicketCreate, TicketUpdate } from "@/schemas/tickets";

type TicketResponse = components["schemas"]["TicketResponse"];

export function useTicketCreate() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: TicketCreate) => {
      return apiClient.post<TicketResponse>("/api/v1/tickets", data);
    },
    onSuccess: (ticket) => {
      toast.success("Ticket created");
      navigate(`/tickets/${ticket.id}`);
      queryClient.invalidateQueries({ queryKey: queryKey.tickets.all() });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
  return { mutate, isPending };
}

export function useTicketUpdate(ticketId: string) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: TicketUpdate) => {
      return apiClient.put<TicketResponse>(`/api/v1/tickets/${ticketId}`, data);
    },
    onSuccess: (ticket) => {
      toast.success("Ticket updated");
      navigate(`/tickets/${ticket.id}`);
      queryClient.invalidateQueries({ queryKey: queryKey.tickets.all() });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
  return { mutate, isPending };
}

export function useTicketDelete(ticketId: string) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { mutate, isPending } = useMutation({
    mutationFn: async () => {
      await apiClient.delete(`/api/v1/tickets/${ticketId}`);
    },
    onSuccess: () => {
      toast.success("Ticket deleted");
      navigate("/tickets");
      queryClient.invalidateQueries({ queryKey: queryKey.tickets.all() });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
  return { mutate, isPending };
}

export function useTicketTransition(ticketId: string) {
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: { status: string }) => {
      return apiClient.put<TicketResponse>(
        `/api/v1/tickets/${ticketId}`,
        data
      );
    },
    onSuccess: () => {
      toast.success("Status updated");
      queryClient.invalidateQueries({ queryKey: queryKey.tickets.all() });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
  return { mutate, isPending };
}
