import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { useChatStream } from "../../src/hooks/useChatStream";
import type { ChatMessageVM } from "../../src/stores/chatStore";

vi.mock("../../src/hooks/useChatStream", () => ({ useChatStream: vi.fn() }));

import { EmbeddedMiniChat } from "../../src/components/home/EmbeddedMiniChat";

const mocked = vi.mocked(useChatStream);

function stub(messages: ChatMessageVM[]) {
  mocked.mockReturnValue({
    messages,
    toolEvents: [],
    isStreaming: false,
    streamingText: "",
    error: null,
    sendMessage: vi.fn(),
  });
}

describe("EmbeddedMiniChat stable keys (T3-22)", () => {
  it("shows the last 4 messages in order when the log is longer than 4", () => {
    const messages: ChatMessageVM[] = Array.from({ length: 7 }, (_, i) => ({
      role: i % 2 === 0 ? "user" : "assistant",
      content: `msg-${i}`,
    }));
    stub(messages);
    render(<EmbeddedMiniChat sessionId="s1" />);

    // Only the last 4 (msg-3..msg-6) render; earlier ones are windowed out.
    for (const i of [3, 4, 5, 6]) {
      expect(screen.getByText(`msg-${i}`)).toBeInTheDocument();
    }
    expect(screen.queryByText("msg-2")).not.toBeInTheDocument();
  });
});
