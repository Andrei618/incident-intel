export interface SourceItem {
  chunk_id: string;
  document_id: string;
  document_title: string;
  chunk_index: number;
  relevance_score: number;
}

export type TokenEvent = { type: "token"; content: string };
export type DoneEvent = {
  type: "done";
  conversation_id: string;
  message_id: string;
  sources: SourceItem[];
  route_used: "sql" | "hybrid" | "clarity";
  confidence: number | null;
};
export type ErrorEvent = { type: "error"; message: string };

export type SSEEvent = TokenEvent | DoneEvent | ErrorEvent;

export type Message = {
  role: "user" | "assistant";
  content: string;
  sources: SourceItem[];
};
