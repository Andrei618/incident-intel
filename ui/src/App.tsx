import { lazy, Suspense, type ComponentType } from "react";
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import { RootErrorBoundary } from "@/components/ErrorBoundary";
import { AppLayout } from "@/components/AppLayout";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

const TicketsPage = lazy(() => import("@/pages/TicketsPage"));
const ChatPage = lazy(() => import("@/pages/ChatPage"));
const SearchPage = lazy(() => import("@/pages/SearchPage"));
const TicketDetailPage = lazy(() => import("@/pages/TicketDetailPage"));
const TicketCreatePage = lazy(() => import("@/pages/TicketCreatePage"))
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));

function suspenseRoute(Component: ComponentType) {
  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <Component />
    </Suspense>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    errorElement: <RootErrorBoundary />,
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: "tickets", element: suspenseRoute(TicketsPage) },
      { path: "tickets/new", element: suspenseRoute(TicketCreatePage)},
      { path: "tickets/:ticketId", element: suspenseRoute(TicketDetailPage)},
      { path: "chat", element: suspenseRoute(ChatPage) },
      { path: "search", element: suspenseRoute(SearchPage)},
      { path: "*", element: suspenseRoute(NotFoundPage) },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
