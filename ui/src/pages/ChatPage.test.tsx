import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import ChatPage from "@/pages/ChatPage";
import { server } from "@/test/mocks/server";
import userEvent from "@testing-library/user-event";
import { makeChatSSEHandler } from "@/test/mocks/handlers";

it("intergration tests happy path", async () => {
  server.use(makeChatSSEHandler());
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  server.use(
    makeChatSSEHandler(),
    http.get("*/api/v1/conversations", () =>
      HttpResponse.json({ items: [], total: 0 })
    )
  );
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    </QueryClientProvider>
  );

  const user = userEvent.setup();

  const input = screen.getByRole("textbox");
  const sendButton = screen.getByRole("button", { name: "Send" });

  await user.type(input, "test question");
  await user.click(sendButton);

  await waitFor(() => screen.getByText(/Hello/));
  expect(screen.getByText(/Hello/)).toBeInTheDocument();
});
