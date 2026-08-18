import { QueryClientProvider } from "@tanstack/react-query";
import type { Router } from "@remix-run/router";
import { RouterProvider } from "react-router-dom";

import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { queryClient } from "./lib/queryClient";
import { router as defaultRouter } from "./router";

interface AppProps {
  router?: Router;
}

export function App({ router = defaultRouter }: AppProps) {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
