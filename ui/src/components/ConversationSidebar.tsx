import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useConversations } from "@/hooks/useConversations";
import { formatTimestamp } from "@/utils/formatTimestamp";
import { Button } from "@/components/ui/button";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import {
  AlertDialog,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog";
import { Trash2 } from "lucide-react";
import { apiClient } from "@/lib/apiClient";
import { toast } from "sonner";
import { queryKey } from "@/lib/queryKeys";

type Props = {
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
};

export function ConversationSidebar({ activeId, onSelect, onNewChat }: Props) {
  const { conversations, isLoading, error } = useConversations();
  const queryClient = useQueryClient();
  const { mutate, isPending } = useMutation({
    mutationFn: async (conversationId: string) => {
      await apiClient.delete(`/api/v1/conversations/${conversationId}`);
    },
    onSuccess: (_, deleteId: string) => {
      toast.success("Conversation deleted");
      queryClient.invalidateQueries({ queryKey: queryKey.conversations.all() });
      if (deleteId === activeId) onNewChat();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  return (
    <div className="w-56 shrink-0 hidden sm:flex flex-col border-r p-2">
      <Button onClick={onNewChat}>New Chat</Button>
      <div className="flex-1 overflow-y-auto flex flex-col gap-1 mt-2">
        {isLoading && (
          <div className="space-y-3">
            <LoadingSkeleton className="h-8" />
            <LoadingSkeleton className="h-8" />
            <LoadingSkeleton className="h-8" />
            <LoadingSkeleton className="h-8" />
          </div>
        )}
        {error && (
          <p className="text-destructive mb-3">Error: {error.message}</p>
        )}
        {conversations && conversations.items.length === 0 && (
          <p className="text-xs text-muted-foreground px-2 py-4">
            No conversation yet
          </p>
        )}
        {conversations?.items.map((item) => (
          <div key={item.id} className="flex items-center group">
            <Button
              variant="ghost"
              className={
                item.id === activeId
                  ? "bg-accent text-accent-foreground justify-start flex-1"
                  : "hover:bg-accent/50 justify-start flex-1"
              }
              onClick={() => onSelect(item.id)}
            >
              {formatTimestamp(item.created_at)}
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100"
                  aria-label="Delete conversation"
                >
                  <Trash2 className="size-3" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete conversation</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => mutate(item.id)}
                    disabled={isPending}
                  >
                    Confirm
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        ))}
      </div>
    </div>
  );
}
