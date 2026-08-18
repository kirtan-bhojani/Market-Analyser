import { createBrowserRouter, createMemoryRouter } from "react-router-dom";

import { RequireAuth } from "./components/auth/RequireAuth";
import { RouteErrorElement } from "./components/common/ErrorBoundary";
import { AppShell } from "./components/layout/AppShell";
import { Analytics } from "./pages/Analytics";
import { BacktestResults } from "./pages/BacktestResults";
import { ChartsPage } from "./pages/Charts";
import { Chat } from "./pages/Chat";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { ML } from "./pages/ML";
import MLModels from "./pages/MLModels";
import { Register } from "./pages/Register";
import { Scanner } from "./pages/Scanner";
import { Settings } from "./pages/Settings";
import { Strategies } from "./pages/Strategies";
import { Trends } from "./pages/Trends";
import Universe from "./pages/Universe";
import { WatchlistPage } from "./pages/Watchlist";

const routes = [
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        errorElement: <RouteErrorElement />,
        children: [
          { path: "/", element: <Home /> },
          { path: "/charts", element: <ChartsPage /> },
          { path: "/watchlist", element: <WatchlistPage /> },
          { path: "/universe", element: <Universe /> },
          { path: "/scanner", element: <Scanner /> },
          { path: "/strategies", element: <Strategies /> },
          { path: "/trends", element: <Trends /> },
          { path: "/analytics", element: <Analytics /> },
          { path: "/backtests/:id", element: <BacktestResults /> },
          { path: "/ml", element: <ML /> },
          { path: "/ml/:id", element: <MLModels /> },
          { path: "/chat", element: <Chat /> },
          { path: "/settings", element: <Settings /> },
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(routes);

export function createTestRouter(initialPath: string) {
  return createMemoryRouter(routes, { initialEntries: [initialPath] });
}
