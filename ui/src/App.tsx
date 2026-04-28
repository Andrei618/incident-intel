import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootErrorBoundary } from "@/components/ErrorBoundary";

const TicketsPage = lazy(() => import("@/pages/TicketsPage"))
const ChatPage = lazy(() => import("@/pages/ChatPage"))

const router = createBrowserRouter([
  {
    path: "/",
    errorElement: <RootErrorBoundary />,
    children: [
      {
        path: "tickets",
        element: (
          <Suspense fallback={<div>Loading...</div>}>
            <TicketsPage />
          </Suspense>
        ),
      },
      {
        path: "chat",
        element: (
          <Suspense fallback={<div>Loading...</div>}>
            <ChatPage />
          </Suspense>
        )
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
