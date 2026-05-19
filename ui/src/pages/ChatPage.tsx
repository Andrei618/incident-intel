import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUp, Square } from "lucide-react";
import { useChatStream } from "@/lib/useChatStream";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/Markdown";
import type { Message } from "@/types/chat";
import { useConversation } from "@/hooks/useConversation";

export default function ChatPage() {
  const { answer, sources, isStreaming, error, thinkingMs, submit, abort } =
    useChatStream();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchParams, setSearchParams] = useSearchParams();
  const conversationId = searchParams.get("conversation_id");
  const {
    conversation,
    isLoading: isHydrating,
    error: hydrationError,
  } = useConversation(conversationId ?? "");

  useEffect(() => {
    if (answer === "") return;
    setMessages((prev) => [
      ...prev.slice(0, -1),
      { role: "assistant", content: answer },
    ]);
  }, [answer]);

  useEffect(() => {
    if (!conversation) return;
    if (messages.length > 0) return;
    setMessages(
      conversation.messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))
    );
  }, [conversation]);

  async function handleSend(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: input },
      { role: "assistant", content: "" },
    ]);
    const newId = await submit(input, conversationId);
    if (newId) {
      setSearchParams({ conversation_id: newId });
    }
    setInput("");
  }

  const showThinking = isStreaming && answer === "";

  return (
    <div
      className={`flex flex-col flex-1 min-h-0 ${CONTENT_MAX_WIDTH} mx-auto w-full`}
    >
      <div className="flex-1 min-h-0 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center text-center text-muted-foreground gap-2">
            <p className="text-lg font-medium">
              Ask about incidents, tickets, or documentation
            </p>
            <p className="text-sm font-medium">
              Type a question to get AI-powered answers from your runbooks
            </p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            className={msg.role === "user" ? "flex justify-end" : ""}
            key={index}
          >
            {msg.role === "user" && (
              <div className="bg-primary text-primary-foreground rounded-2xl px-4 py-2 max-w-[80%]">
                {msg.content}
              </div>
            )}
            {msg.role === "assistant" && msg.content && (
              <div className="bg-muted rounded-2xl px-4 py-2">
                <Markdown>{msg.content}</Markdown>
              </div>
            )}
          </div>
        ))}

        {showThinking && (
          <p className="text-sm text-muted-foreground animate-pulse">
            Thinking...{(thinkingMs / 1000).toFixed(1)}s
          </p>
        )}
        {error && <p className="text-sm text-destructive">Error: {error}</p>}
        {sources.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Sources</p>
            {sources.map((s) => (
              <div
                key={s.chunk_id}
                className="flex items-center justify-between rounded bg-muted px-3 py-1.5 text-sm"
              >
                <Link
                  to={`/documents/${s.document_id}`}
                  className="hover:underline"
                >
                  {s.document_title}
                </Link>
                <span>{Math.round(s.relevance_score * 100)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <form onSubmit={handleSend} className="flex gap-2 pt-4 border-t">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
          placeholder="Ask about incidents, tickets, or documentation..."
          className="rounded-full"
        />
        <Button
          type={isStreaming ? "button" : "submit"}
          onClick={isStreaming ? abort : undefined}
          disabled={!isStreaming && !input.trim()}
          variant="ghost"
          size="icon"
          aria-label={isStreaming ? "Stop" : "Send"}
        >
          {isStreaming ? (
            <Square className="size-4" />
          ) : (
            <ArrowUp className="size-4" />
          )}
        </Button>
      </form>
    </div>
  );
}
