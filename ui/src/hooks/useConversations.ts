import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import { conversationListSchema } from "@/schemas/api/conversation";

export function useConversations() {
  const {
    data: conversations,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.conversations.all(),
    queryFn: () =>
      apiClient.get("/api/v1/conversations", conversationListSchema),
  });
  return { conversations, isLoading, error };
}
