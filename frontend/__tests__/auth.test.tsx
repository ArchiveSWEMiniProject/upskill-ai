import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import HomePage from "@/app/(m1)/page";
import { getToken, setToken } from "@/lib/api";
import { mockApi } from "@/test-utils/api";

const mockPush = jest.fn();
const mockReplace = jest.fn();
const mockRouter = { push: mockPush, replace: mockReplace };
jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));

const TOKEN = { status: 200, body: { access_token: "signed.jwt.token", token_type: "bearer" } };

function logInForm() {
  return screen.getByRole("form", { name: "Log in" });
}

function registerForm() {
  return screen.getByRole("form", { name: "Create a student account" });
}

async function fill(form: HTMLElement, email: string, password: string) {
  const user = userEvent.setup();
  const [emailBox, passwordBox] = form.querySelectorAll("input");
  await user.type(emailBox, email);
  if (password) await user.type(passwordBox, password);
  await user.click(form.querySelector("button")!);
}

test("logging in stores the token and opens the profile", async () => {
  const calls = mockApi({ "POST /auth/login": TOKEN });
  render(<HomePage />);
  await fill(logInForm(), "asha@pes.edu", "Upskill2026");
  expect(calls[0].body).toEqual({ email: "asha@pes.edu", password: "Upskill2026" });
  expect(getToken()).toBe("signed.jwt.token");
  expect(mockPush).toHaveBeenCalledWith("/profile");
});

test("failed login shows the API's generic message and stays on the page", async () => {
  mockApi({ "POST /auth/login": { status: 401, body: { detail: "Invalid email or password" } } });
  render(<HomePage />);
  await fill(logInForm(), "asha@pes.edu", "wrong");
  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  expect(getToken()).toBeNull();
  expect(mockPush).not.toHaveBeenCalled();
});

test("registration errors are shown next to the field that failed", async () => {
  mockApi({
    "POST /auth/register": {
      status: 422,
      body: {
        detail: [{ loc: ["body", "password"], msg: "Value error, Password must contain at least one letter and one digit" }],
      },
    },
  });
  render(<HomePage />);
  await fill(registerForm(), "asha@pes.edu", "abcdefgh");
  const password = registerForm().querySelector('input[name="password"]')!;
  expect(password).toHaveAttribute("aria-invalid", "true");
  expect(password).toHaveAccessibleDescription(
    expect.stringContaining("Password must contain at least one letter and one digit"),
  );
  expect(registerForm().querySelector('input[name="email"]')).toHaveAttribute("aria-invalid", "false");
});

test("registering logs straight in and lands on the profile", async () => {
  const calls = mockApi({
    "POST /auth/register": { status: 201, body: { user_id: 3, email: "asha@pes.edu", role: "student" } },
    "POST /auth/login": TOKEN,
  });
  render(<HomePage />);
  await fill(registerForm(), "asha@pes.edu", "Upskill2026");
  expect(calls.map((c) => c.path)).toEqual(["/auth/register", "/auth/login"]);
  expect(calls[0].body).toEqual({ email: "asha@pes.edu", password: "Upskill2026" });
  expect(mockPush).toHaveBeenCalledWith("/profile");
});

test("a duplicate email is reported for the whole form", async () => {
  mockApi({ "POST /auth/register": { status: 400, body: { detail: "A user with this email already exists" } } });
  render(<HomePage />);
  await fill(registerForm(), "asha@pes.edu", "Upskill2026");
  expect(await screen.findByRole("alert")).toHaveTextContent("A user with this email already exists");
});

test("an unreachable server is reported, not swallowed", async () => {
  global.fetch = jest.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  render(<HomePage />);
  await fill(logInForm(), "asha@pes.edu", "Upskill2026");
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the server");
});

test("a student who is already logged in goes straight to the profile", () => {
  setToken("signed.jwt.token");
  render(<HomePage />);
  expect(mockReplace).toHaveBeenCalledWith("/profile");
});
