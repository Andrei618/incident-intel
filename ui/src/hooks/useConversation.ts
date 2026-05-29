import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import { conversationDetailSchema } from "@/schemas/api/conversation";

export function useConversation(conversationId: string) {
  const {
    data: conversation,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.conversations.detail(conversationId),
    queryFn: () =>
      apiClient.get(
        `/api/v1/conversations/${conversationId}`,
        conversationDetailSchema
      ),
    enabled: !!conversationId,
  });
  return { conversation, isLoading, error };
}
