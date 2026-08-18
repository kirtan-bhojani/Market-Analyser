import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { RuleBuilder } from "../../src/components/scanner/RuleBuilder";

describe("RuleBuilder save gating (T3-21)", () => {
  it("disables Save until the rule name is non-empty", () => {
    const onSubmit = vi.fn();
    render(<RuleBuilder onSubmit={onSubmit} />);

    const save = screen.getByTestId("save-rule");
    expect(save).toBeDisabled();

    // A whitespace-only name is still empty.
    fireEvent.change(screen.getByTestId("rule-name-input"), { target: { value: "   " } });
    expect(save).toBeDisabled();

    fireEvent.change(screen.getByTestId("rule-name-input"), { target: { value: "RSI dip" } });
    expect(save).toBeEnabled();

    fireEvent.click(save);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
