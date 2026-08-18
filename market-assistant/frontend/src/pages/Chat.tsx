import { useEffect, useRef, useState } from "react";

import { EmptyState } from "../components/common/EmptyState";
import { FollowUpChips } from "../components/chat/FollowUpChips";
import { MessageBubble } from "../components/chat/MessageBubble";
import { SessionsSidebar } from "../components/chat/SessionsSidebar";
import { ToolActivityIndicator } from "../components/chat/ToolActivityIndicator";
import { useChatStream } from "../hooks/useChatStream";
import { createSession, getSessionMessages, listSessions } from "../lib/api";
import { useChatStore } from "../stores/chatStore";

const FOLLOW_UPS = [
  "How is BTC looking on the 1h?",
  "What strategy fits the current regime?",
  "What's the market breadth right now?",
];

export function Chat() {
  const { setSessions, setActiveSession, activeSessionId, setMessages } = useChatStore();
  const [draft, setDraft] = useState("");
  const sessionId = activeSessionId ?? "";
  const { messages, toolEvents, isStreaming, streamingText, error, sendMessage } =
    useChatStream(sessionId);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load existing sessions and open (or create) one on first mount. Resilient to
  // a backend being down — the composer and empty state still render.
  useEffect(() => {
    let cancelled = false;
    listSessions()
      .then(async (sessions) => {
        if (cancelled) return;
        setSessions(sessions);
        if (sessions.length > 0) {
          setActiveSession(sessions[0].id);
        } else {
          const created = await createSession();
          if (cancelled) return;
          setSessions([created]);
          setActiveSession(created.id);
        }
      })
      .catch(() => {
        /* offline — leave the page in its empty state */
      });
    return () => {
      cancelled = true;
    };
  }, [setSessions, setActiveSession]);

  // Hydrate history when switching sessions.
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    getSessionMessages(sessionId)
      .then((history) => {
        if (!cancelled) setMessages(sessionId, history);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [sessionId, setMessages]);

  useEffect(() => {
    // scrollTo is absent in jsdom (unit tests); guard the method itself.
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight });
  }, [messages.length, streamingText, toolEvents.length]);

  const startNewSession = () => {
    createSession()
      .then((created) => {
        setSessions([created, ...useChatStore.getState().sessions]);
        setActiveSession(created.id);
      })
      .catch(() => {});
  };

  const submit = (text: string) => {
    void sendMessage(text);
    setDraft("");
  };

  const hasConversation = messages.length > 0 || isStreaming;

  return (
    <>
      <h1 className="page-title">Chat</h1>
      <p className="page-sub">Ask about the market · grounded in your live indicators</p>

      <div className="chat-page">
        <SessionsSidebar onSelect={setActiveSession} onNew={startNewSession} />

        <section className="chat-main panel" aria-label="Conversation">
          <div className="chat-scroll" ref={scrollRef}>
            {!hasConversation && (
              <EmptyState
                glyph="✦"
                title="Start a conversation"
                message="Ask about a symbol, a setup, or the current regime. Answers stream with the tools they checked; recommendation answers carry the standard disclaimer."
              />
            )}

            {/* Full append-only log: a message keeps its index for life, so the
                index IS its stable identity here (unlike the sliced mini-chat). */}
            {messages.map((m, i) => (
              <MessageBubble key={i} message={m} />
            ))}

            {isStreaming && (
              <div className="chat-thinking">
                {toolEvents.length > 0 && (
                  <div className="tool-activity-row">
                    {toolEvents.map((e, i) => (
                      <ToolActivityIndicator key={i} event={e} />
                    ))}
                  </div>
                )}
                {streamingText ? (
                  <MessageBubble message={{ role: "assistant", content: streamingText }} />
                ) : (
                  <span className="chat-typing" aria-label="Assistant is thinking">
                    <i />
                    <i />
                    <i />
                  </span>
                )}
              </div>
            )}

            {error && <p className="chat-error">{error}</p>}
          </div>

          <div className="chat-composer">
            <FollowUpChips suggestions={FOLLOW_UPS} onPick={submit} disabled={isStreaming} />
            <form
              className="chat-input-row"
              onSubmit={(e) => {
                e.preventDefault();
                submit(draft);
              }}
            >
              <input
                className="chat-input"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask about a symbol, setup, or the market…"
                disabled={isStreaming || !sessionId}
                aria-label="Message"
              />
              <button
                type="submit"
                className="chat-send"
                disabled={isStreaming || !draft.trim() || !sessionId}
              >
                Send
              </button>
            </form>
          </div>
        </section>
      </div>
    </>
  );
}
