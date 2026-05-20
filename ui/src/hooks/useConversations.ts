import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import type { components } from "@/types/api";

type ConversationListResponse =
  components["schemas"]["ConversationListResponse"];

export function useConversations() {
  const {
    data: conversations,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.conversations.all(),
    queryFn: () =>
      apiClient.get<ConversationListResponse>("/api/v1/conversations"),
  });
  return { conversations, isLoading, error };
}
