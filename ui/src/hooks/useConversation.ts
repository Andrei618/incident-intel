import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import type { components } from "@/types/api";

type ConversationDetailResponse =
  components["schemas"]["ConversationDetailResponse"];

export function useConversation(conversationId: string) {
  const {
    data: conversation,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.conversations.detail(conversationId),
    queryFn: () =>
      apiClient.get<ConversationDetailResponse>(
        `/api/v1/conversations/${conversationId}`
      ),
    enabled: !!conversationId,
  });
  return { conversation, isLoading, error };
}
