import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ErrorBoundary, RouteErrorElement } from "../../src/components/common/ErrorBoundary";

function Boom(): never {
  throw new Error("kaboom");
}

describe("ErrorBoundary", () => {
  beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => {}));
  afterEach(() => vi.restoreAllMocks());

  it("renders the fallback when a child throws", () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("renders children when nothing throws", () => {
    render(
      <ErrorBoundary>
        <span>safe</span>
      </ErrorBoundary>,
    );
    expect(screen.getByText("safe")).toBeInTheDocument();
    expect(screen.queryByTestId("error-boundary")).toBeNull();
  });
});

describe("RouteErrorElement", () => {
  beforeEach(() => vi.spyOn(console, "error").mockImplementation(() => {}));
  afterEach(() => vi.restoreAllMocks());

  it("catches a route render error instead of white-screening", () => {
    const router = createMemoryRouter(
      [{ path: "/", element: <Boom />, errorElement: <RouteErrorElement /> }],
      { initialEntries: ["/"] },
    );
    render(<RouterProvider router={router} />);
    expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
  });
});
