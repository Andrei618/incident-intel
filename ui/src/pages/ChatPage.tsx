import React, { useState } from "react";
import { useChatStream } from "@/lib/useChatStream";

export default function ChatPage() {
  const { answer, sources, isStreaming, error, thinkingMs, submit, abort } =
    useChatStream();
  const [input, setInput] = useState("");
  const [submittedMessage, setSubmittedMessage] = useState("");

  function handleSend(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setSubmittedMessage(input);
    submit(input);
    setInput("");
  }

  const showThinking = isStreaming && answer === "";

  return (
    <div>
      <h1>Chat</h1>

      {submittedMessage && (
        <p>
          <strong>You:</strong> {submittedMessage}
        </p>
      )}
      {answer && (
        <p>
          <strong>Assistant:</strong> {answer}
        </p>
      )}
      {showThinking && <p>Thinking...{(thinkingMs / 1000).toFixed(1)}s</p>}
      {error && <p>Error: {error}</p>}
      {sources.length > 0 && (
        <ul>
          {sources.map((s) => (
            <li key={s.chunk_id}>{s.document_title}</li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button type="button" onClick={abort}>
            Stop
          </button>
        ) : (
          <button type="submit">Send</button>
        )}
      </form>
    </div>
  );
}
