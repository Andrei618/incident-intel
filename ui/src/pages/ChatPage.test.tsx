import { render, screen, waitFor } from "@testing-library/react";
import ChatPage from "@/pages/ChatPage";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import userEvent from "@testing-library/user-event";

it("intergration tests happy path", async () => {
  server.use(
    http.post("*/api/v1/chat", () => {
      const encoder = new TextEncoder();
      const body = new ReadableStream({
        start(controller) {
          controller.enqueue(
            encoder.encode('data: {"type":"token","content":"Hello"}\n\n')
          );
          const done = {
            type: "done",
            conversation_id: "c1",
            message_id: "m1",
            sources: [],
            route_used: "hybrid",
            confidence: null,
          };
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(done)}\n\n`)
          );
          controller.close();
        },
      });
      return new HttpResponse(body, {
        headers: { "Content-Type": "text/event-stream" },
      });
    })
  );
  render(<ChatPage />);

  const user = userEvent.setup();

  const input = screen.getByRole("textbox");
  const sendButton = screen.getByRole("button", { name: "Send" });

  await user.type(input, "test question");
  await user.click(sendButton);

  await waitFor(() => screen.getByText(/Hello/));
  expect(screen.getByText(/Hello/)).toBeInTheDocument();
});
