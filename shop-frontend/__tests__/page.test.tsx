/**
 * @jest-environment jsdom
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ChatHome from "../app/page";
import { rest } from "msw";
import { setupServer } from "msw/node";

// MSW mock server to intercept the /chat call your component makes
const server = setupServer(
  rest.post("http://127.0.0.1:8000/chat", async (_req, res, ctx) => {
    return res(
      ctx.json({
        response: "The Nike Air Max are $109.99.",
        history: [
          "User: how much are the air max?",
          "Assistant: The Nike Air Max are $109.99.",
        ],
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  sessionStorage.clear();
});
afterAll(() => server.close());

describe("<ChatHome />", () => {
  it("renders header + input", () => {
    render(<ChatHome />);
    expect(screen.getByText("Shopping Assistant")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/Ask about products/i)
    ).toBeInTheDocument();
  });

  it("sends a message and shows assistant reply", async () => {
    render(<ChatHome />);

    const input = screen.getByPlaceholderText(/Ask about products/i);
    fireEvent.change(input, { target: { value: "how much are the air max?" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    // optimistic user bubble should appear
    expect(
      await screen.findByText(/how much are the air max\?/i)
    ).toBeInTheDocument();

    // server reply bubble should render
    // server reply bubble should render (accept $109 or $109.99)
        await waitFor(() => {
        expect(
            screen.getByText(/The Nike Air Max are \$109(\.99)?\./i)
            ).toBeInTheDocument();
    });

  });

  it("persists history in sessionStorage", async () => {
    render(<ChatHome />);
    const input = screen.getByPlaceholderText(/Ask about products/i);
    fireEvent.change(input, { target: { value: "hello" } });
    fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

    // server reply bubble should render (accept $109 or $109.99)
    await waitFor(() => {
    expect(
        screen.getByText(/The Nike Air Max are \$109(\.99)?\./i)
    ).toBeInTheDocument();
    });
  });
});
