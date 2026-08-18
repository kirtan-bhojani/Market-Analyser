import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

const createMutate = vi.fn();

vi.mock("../../../src/hooks/useScanRules", () => ({
  useScanRules: () => ({
    rules: [
      { id: 1, name: "RSI dip", definition: { all: [] }, enabled: true },
      { id: 2, name: "Gap up", definition: { all: [] }, enabled: true },
    ],
  }),
}));

vi.mock("../../../src/hooks/useAlertSubscriptions", () => ({
  useAlertSubscriptions: () => ({
    create: { mutate: createMutate, isPending: false, isError: false, error: null },
  }),
}));

import { AlertSubscriptionForm } from "../../../src/components/settings/AlertSubscriptionForm";

describe("AlertSubscriptionForm", () => {
  beforeEach(() => {
    createMutate.mockReset();
  });

  it("submits the expected payload for the selected rule and target", () => {
    render(<AlertSubscriptionForm />);

    fireEvent.change(screen.getByLabelText("Scan rule"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Telegram chat id"), {
      target: { value: "123456789" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add subscription" }));

    expect(createMutate).toHaveBeenCalledWith(
      { rule_id: 2, channel: "telegram", target: "123456789" },
      expect.anything(),
    );
  });

  it("shows a validation error and does not call create when the target is empty", () => {
    render(<AlertSubscriptionForm />);

    fireEvent.change(screen.getByLabelText("Scan rule"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Add subscription" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Pick a rule and enter a telegram target.",
    );
    expect(createMutate).not.toHaveBeenCalled();
  });
});
