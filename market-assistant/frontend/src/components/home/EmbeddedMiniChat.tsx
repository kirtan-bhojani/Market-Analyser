import { useState } from "react";

import { useChatStream } from "../../hooks/useChatStream";
import { MessageBubble } from "../chat/MessageBubble";

/** Compact desk chat that reuses the full chat stream + message bubbles. */
export function EmbeddedMiniChat({ sessionId }: { sessionId: string }) {
  const { messages, isStreaming, streamingText, error, sendMessage } =
    useChatStream(sessionId);
  const [text, setText] = useState("");

  return (
    <div className="embedded-mini-chat" data-testid="embedded-mini-chat">
      <div className="mini-chat-log">
        {messages.slice(-4).map((m, i) => {
          // Key by absolute position in the full (append-only) log, not the
          // sliced index — otherwise every new message shifts the window and
          // React reuses the wrong bubble's DOM/state for the last 4.
          const key = messages.length - Math.min(4, messages.length) + i;
          return <MessageBubble key={key} message={m} />;
        })}
        {isStreaming && streamingText && (
          <div className="chat-bubble chat-bubble--assistant">
            <p className="chat-bubble-body">{streamingText}</p>
          </div>
        )}
        {error && (
          <p className="chat-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <form
        className="chatbox"
        onSubmit={(e) => {
          e.preventDefault();
          const trimmed = text.trim();
          if (trimmed) {
            void sendMessage(trimmed);
            setText("");
          }
        }}
      >
        <input
          aria-label="Ask the assistant"
          placeholder="Ask about the market…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={isStreaming}
        />
        <button type="submit" disabled={isStreaming}>
          Ask
        </button>
      </form>
    </div>
  );
}
