import { Component, type ErrorInfo, type ReactNode } from "react";
import { useRouteError } from "react-router-dom";

interface FallbackProps {
  message: string;
}

/** Shared crash UI used by both the class boundary and the route error element. */
function ErrorFallback({ message }: FallbackProps) {
  return (
    <div className="empty" role="alert" data-testid="error-boundary">
      <div className="glyph" aria-hidden="true">
        ⚠
      </div>
      <h3>Something went wrong</h3>
      <p>{message}</p>
      <button className="cta" type="button" onClick={() => window.location.reload()}>
        Reload
      </button>
    </div>
  );
}

function messageFromError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "An unexpected error occurred.";
}

/**
 * Route-level error element for react-router. Catches render/loader errors
 * thrown anywhere below the route it is attached to, so one broken page never
 * white-screens the whole app.
 */
export function RouteErrorElement() {
  const error = useRouteError();
  return <ErrorFallback message={messageFromError(error)} />;
}

interface ErrorBoundaryState {
  message: string | null;
}

/**
 * Top-level class error boundary — the last-resort net around the router itself
 * (render errors outside any route's element, e.g. in providers). Route-scoped
 * errors are handled by RouteErrorElement.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { message: null };

  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return { message: messageFromError(error) };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught", error, info.componentStack);
  }

  render() {
    if (this.state.message !== null) {
      return <ErrorFallback message={this.state.message} />;
    }
    return this.props.children;
  }
}
