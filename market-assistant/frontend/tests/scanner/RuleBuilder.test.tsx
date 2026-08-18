import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { RuleBuilder } from "../../src/components/scanner/RuleBuilder";

describe("RuleBuilder", () => {
  it("emits the exact DSL for RSI(5m)<30 AND relVol>2", () => {
    const onSubmit = vi.fn();
    render(<RuleBuilder onSubmit={onSubmit} />);

    fireEvent.change(screen.getByTestId("rule-name-input"), { target: { value: "RSI dip" } });

    fireEvent.change(screen.getByTestId("row-0-indicator"), { target: { value: "rsi" } });
    fireEvent.change(screen.getByTestId("row-0-tf"), { target: { value: "5m" } });
    fireEvent.change(screen.getByTestId("row-0-operator"), { target: { value: "<" } });
    fireEvent.change(screen.getByTestId("row-0-value"), { target: { value: "30" } });

    fireEvent.click(screen.getByTestId("add-row"));

    fireEvent.change(screen.getByTestId("row-1-indicator"), { target: { value: "rel_volume" } });
    fireEvent.change(screen.getByTestId("row-1-tf"), { target: { value: "5m" } });
    fireEvent.change(screen.getByTestId("row-1-operator"), { target: { value: ">" } });
    fireEvent.change(screen.getByTestId("row-1-value"), { target: { value: "2" } });

    fireEvent.click(screen.getByTestId("save-rule"));

    expect(onSubmit).toHaveBeenCalledWith(
      {
        all: [
          { ind: "rsi", tf: "5m", op: "<", value: 30 },
          { ind: "rel_volume", tf: "5m", op: ">", value: 2 },
        ],
      },
      "RSI dip",
    );
  });
});
