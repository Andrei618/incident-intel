import { lazy, Suspense } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { RootErrorBoundary } from "@/components/ErrorBoundary";

const TicketsPage = lazy(() => import("@/pages/TicketsPage"))

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
      // stub other routes here with a placeholder element
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
