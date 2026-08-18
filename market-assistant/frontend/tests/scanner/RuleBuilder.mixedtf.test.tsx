import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { RuleBuilder } from "../../src/components/scanner/RuleBuilder";
import type { RuleDefinition } from "../../src/lib/scannerTypes";

describe("RuleBuilder timeframe consistency", () => {
  it("keeps a newly added condition on the chosen timeframe (no mixed-tf rule)", () => {
    const onSubmit = vi.fn();
    render(<RuleBuilder onSubmit={onSubmit} />);

    fireEvent.change(screen.getByTestId("rule-name-input"), { target: { value: "TF rule" } });
    fireEvent.change(screen.getByTestId("row-0-tf"), { target: { value: "1h" } });
    fireEvent.click(screen.getByTestId("add-row"));
    fireEvent.click(screen.getByTestId("save-rule"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const def = onSubmit.mock.calls[0][0] as RuleDefinition;
    expect(def.all).toHaveLength(2);
    // The mixed-tf bug added the second row at the default "5m".
    expect(def.all.every((c) => c.tf === "1h")).toBe(true);
  });
});
