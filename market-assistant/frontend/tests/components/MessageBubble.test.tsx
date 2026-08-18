import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { MessageBubble } from "../../src/components/chat/MessageBubble";

const DISCLAIMER = "Educational analysis. Not investment advice. Past performance ≠ future results.";

describe("MessageBubble", () => {
  it("renders the disclaimer on an assistant recommendation message", () => {
    render(
      <MessageBubble message={{ role: "assistant", content: `Setup detected on the 1h. ${DISCLAIMER}` }} />,
    );
    expect(screen.getByText(new RegExp(DISCLAIMER))).toBeInTheDocument();
  });

  it("renders assistant content verbatim without adding imperative framing", () => {
    render(<MessageBubble message={{ role: "assistant", content: "RSI is elevated on the 1h." }} />);
    expect(screen.getByText("RSI is elevated on the 1h.")).toBeInTheDocument();
    expect(screen.queryByText(/guaranteed/i)).not.toBeInTheDocument();
  });

  it("renders user messages without a disclaimer", () => {
    render(<MessageBubble message={{ role: "user", content: "how is BTC looking?" }} />);
    expect(screen.queryByText(new RegExp(DISCLAIMER))).not.toBeInTheDocument();
  });
});
