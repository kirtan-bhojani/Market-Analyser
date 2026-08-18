import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DelayBadge } from "../../src/components/common/DelayBadge";

describe("DelayBadge", () => {
  it("renders the delay label when delayed", () => {
    render(<DelayBadge delayed={true} delayMinutes={15} />);
    expect(screen.getByText("15-min delayed")).toBeInTheDocument();
  });

  it("renders nothing when not delayed", () => {
    const { container } = render(<DelayBadge delayed={false} delayMinutes={0} />);
    expect(container).toBeEmptyDOMElement();
  });
});
