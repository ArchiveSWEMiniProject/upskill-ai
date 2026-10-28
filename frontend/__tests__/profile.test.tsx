import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ProfilePage from "@/app/(m1)/profile/page";
import { getToken, setToken } from "@/lib/api";
import { mockApi, PROFILE } from "@/test-utils/api";

const mockReplace = jest.fn();
// Next's useRouter returns the same object on every render; so must the mock.
const mockRouter = { push: jest.fn(), replace: mockReplace };
jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));

beforeEach(() => setToken("signed.jwt.token"));

test("without a token the page sends the visitor to log in", () => {
  sessionStorage.clear();
  global.fetch = jest.fn();
  render(<ProfilePage />);
  expect(mockReplace).toHaveBeenCalledWith("/");
  expect(global.fetch).not.toHaveBeenCalled();
});

test("the profile is requested with the token and shown", async () => {
  const calls = mockApi({ "GET /profile": { status: 200, body: PROFILE } });
  render(<ProfilePage />);
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
  expect(calls).toHaveLength(1);
  expect(calls[0].headers.Authorization).toBe("Bearer signed.jwt.token");
});

test("a new student creates their profile, and blank fields are reported", async () => {
  const calls = mockApi({
    "GET /profile": { status: 404, body: { detail: "Profile not found" } },
    "POST /profile": [
      { status: 422, body: { detail: [{ loc: ["body", "name"], msg: "String should have at least 1 character" }] } },
      { status: 201, body: PROFILE },
    ],
  });
  const user = userEvent.setup();
  render(<ProfilePage />);
  const create = await screen.findByRole("button", { name: "Create profile" });

  await user.click(create);
  expect(screen.getByRole("textbox", { name: /Name/ })).toHaveAttribute("aria-invalid", "true");

  await user.type(screen.getByRole("textbox", { name: /Name/ }), "  Asha Rao ");
  await user.click(create);
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
  expect(calls.at(-1)?.body).toEqual({ name: "Asha Rao", education_level: null });
});

test("an expired token logs the student out", async () => {
  mockApi({ "GET /profile": { status: 401, body: { detail: "Not authenticated" } } });
  render(<ProfilePage />);
  await screen.findByText("UpSkill-AI");
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(mockReplace).toHaveBeenCalledWith("/");
  expect(getToken()).toBeNull();
});

test("a non-student account is told the page is for students", async () => {
  mockApi({ "GET /profile": { status: 403, body: { detail: "Only students can manage a student profile" } } });
  render(<ProfilePage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This page is for student accounts.");
});

test("log out clears the token", async () => {
  mockApi({ "GET /profile": { status: 200, body: PROFILE } });
  render(<ProfilePage />);
  await userEvent.setup().click(screen.getByRole("button", { name: "Log out" }));
  expect(getToken()).toBeNull();
  expect(mockReplace).toHaveBeenCalledWith("/");
});
