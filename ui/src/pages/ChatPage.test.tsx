import { render, screen, waitFor } from "@testing-library/react";
import ChatPage from "@/pages/ChatPage";
import { server } from "@/test/mocks/server";
import userEvent from "@testing-library/user-event";
import { makeChatSSEHandler } from "@/test/mocks/handlers";

it("intergration tests happy path", async () => {
  server.use(makeChatSSEHandler());
  render(<ChatPage />);

  const user = userEvent.setup();

  const input = screen.getByRole("textbox");
  const sendButton = screen.getByRole("button", { name: "Send" });

  await user.type(input, "test question");
  await user.click(sendButton);

  await waitFor(() => screen.getByText(/Hello/));
  expect(screen.getByText(/Hello/)).toBeInTheDocument();
});
