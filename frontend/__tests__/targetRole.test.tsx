import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TargetRoleSection } from "@/app/(m1)/_components/TargetRoleSection";
import { setToken } from "@/lib/api";
import { mockApi } from "@/test-utils/api";

const ROLES = [
  { role_id: 1, role_name: "Analyst" },
  { role_id: 2, role_name: "Backend" },
];
const SUMMARY = { role_id: 2, role_name: "Backend", set_at: "2026-11-07T10:00:00Z", required: 3, held: 1, gap: 2 };

beforeEach(() => setToken("signed.jwt.token"));

test("a student with no role sees the choices and picks one to see the gap counts", async () => {
  const calls = mockApi({
    "GET /profile/roles": { status: 200, body: ROLES },
    "GET /profile/target-role": { status: 404, body: { detail: "No target role chosen" } },
    "PUT /profile/target-role": { status: 200, body: SUMMARY },
  });
  const user = userEvent.setup();
  render(<TargetRoleSection onUnauthorized={jest.fn()} />);

  await screen.findByRole("option", { name: "Backend" });
  await user.selectOptions(screen.getByRole("combobox", { name: "Role" }), "Backend");
  await user.click(screen.getByRole("button", { name: "Set target role" }));

  expect(await screen.findByLabelText("Gap summary")).toHaveTextContent(
    "Backend: 3 skills required, you hold 1, gap 2.",
  );
  expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ role_id: 2 });
});

test("the current role is preselected and summarised", async () => {
  mockApi({
    "GET /profile/roles": { status: 200, body: ROLES },
    "GET /profile/target-role": { status: 200, body: SUMMARY },
  });
  render(<TargetRoleSection onUnauthorized={jest.fn()} />);

  expect(await screen.findByLabelText("Gap summary")).toHaveTextContent("Backend");
  expect(screen.getByRole("combobox", { name: "Role" })).toHaveValue("2");
});

test("saving without choosing a role asks for one and sends nothing", async () => {
  const calls = mockApi({
    "GET /profile/roles": { status: 200, body: ROLES },
    "GET /profile/target-role": { status: 404, body: { detail: "No target role chosen" } },
  });
  const user = userEvent.setup();
  render(<TargetRoleSection onUnauthorized={jest.fn()} />);

  await user.click(await screen.findByRole("button", { name: "Set target role" }));

  expect(screen.getByRole("alert")).toHaveTextContent("Choose a role first.");
  expect(calls.some((call) => call.method === "PUT")).toBe(false);
});

test("a rejected role shows the API's message", async () => {
  mockApi({
    "GET /profile/roles": { status: 200, body: ROLES },
    "GET /profile/target-role": { status: 404, body: { detail: "No target role chosen" } },
    "PUT /profile/target-role": { status: 422, body: { detail: "Unknown role" } },
  });
  const user = userEvent.setup();
  render(<TargetRoleSection onUnauthorized={jest.fn()} />);

  await screen.findByRole("option", { name: "Analyst" });
  await user.selectOptions(screen.getByRole("combobox", { name: "Role" }), "Analyst");
  await user.click(screen.getByRole("button", { name: "Set target role" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Unknown role");
});
