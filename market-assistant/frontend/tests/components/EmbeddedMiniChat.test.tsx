import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { useChatStream } from "../../src/hooks/useChatStream";

vi.mock("../../src/hooks/useChatStream", () => ({ useChatStream: vi.fn() }));

import { EmbeddedMiniChat } from "../../src/components/home/EmbeddedMiniChat";

const mocked = vi.mocked(useChatStream);

function stub(overrides: Partial<ReturnType<typeof useChatStream>>) {
  mocked.mockReturnValue({
    messages: [],
    toolEvents: [],
    isStreaming: false,
    streamingText: "",
    error: null,
    sendMessage: vi.fn(),
    ...overrides,
  });
}

describe("EmbeddedMiniChat", () => {
  it("renders the in-progress streaming answer", () => {
    stub({ isStreaming: true, streamingText: "BTC is consolidating" });
    render(<EmbeddedMiniChat sessionId="s1" />);
    expect(screen.getByText("BTC is consolidating")).toBeInTheDocument();
  });

  it("renders an error when the turn fails", () => {
    stub({ error: "The assistant is unavailable right now." });
    render(<EmbeddedMiniChat sessionId="s1" />);
    expect(
      screen.getByText("The assistant is unavailable right now."),
    ).toBeInTheDocument();
  });
});
