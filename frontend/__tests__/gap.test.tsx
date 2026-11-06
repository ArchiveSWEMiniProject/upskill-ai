import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import RoadmapPage from "@/app/(m2)/roadmap/page";
import { getToken, setToken } from "@/lib/api";
import { mockApi } from "@/test-utils/api";

const mockReplace = jest.fn();
// Next's useRouter returns the same object on every render; so must the mock.
const mockRouter = { push: jest.fn(), replace: mockReplace };
jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));

const GAP = {
  role_id: 3,
  role_name: "Backend Developer",
  items: [
    {
      rank: 1, skill_id: 1, skill_name: "Python",
      required_level: "intermediate", current_level: "beginner", weight: 5,
    },
    {
      rank: 2, skill_id: 3, skill_name: "SQL Basics",
      required_level: "beginner", current_level: null, weight: 3,
    },
    {
      rank: 3, skill_id: 4, skill_name: "Docker",
      required_level: "beginner", current_level: null, weight: 1,
    },
  ],
};

beforeEach(() => setToken("signed.jwt.token"));

test("without a token the page sends the visitor to log in", () => {
  sessionStorage.clear();
  global.fetch = jest.fn();
  render(<RoadmapPage />);
  expect(mockReplace).toHaveBeenCalledWith("/");
  expect(global.fetch).not.toHaveBeenCalled();
});

test("the gap is requested with the token and listed most important first", async () => {
  const calls = mockApi({ "GET /roadmap/gap": { status: 200, body: GAP } });
  render(<RoadmapPage />);

  expect(await screen.findByText("Target role: Backend Developer")).toBeInTheDocument();
  const items = screen.getAllByRole("listitem");
  expect(items).toHaveLength(3);
  expect(items[0]).toHaveTextContent("1. Python");
  expect(items[0]).toHaveTextContent("Current: Beginner - Required: Intermediate");
  expect(items[0]).toHaveTextContent("Importance to the role: 5");
  expect(items[1]).toHaveTextContent("2. SQL Basics");
  expect(items[1]).toHaveTextContent("Current: Not held yet - Required: Beginner");
  expect(items[2]).toHaveTextContent("3. Docker");
  expect(calls[0].headers.Authorization).toBe("Bearer signed.jwt.token");
});

test("a student with no gap is told they meet every requirement", async () => {
  mockApi({ "GET /roadmap/gap": { status: 200, body: { ...GAP, items: [] } } });
  render(<RoadmapPage />);

  expect(
    await screen.findByText("You already meet every requirement for Backend Developer."),
  ).toBeInTheDocument();
  expect(screen.queryByRole("list")).not.toBeInTheDocument();
});

test("a student without a target role is asked to choose one", async () => {
  mockApi({
    "GET /roadmap/gap": { status: 409, body: { detail: "Choose a target role to see your skill gap" } },
  });
  render(<RoadmapPage />);

  expect(await screen.findByText("Choose a target role to see your skill gap.")).toBeInTheDocument();
});

test("a student without a profile is pointed to the profile page", async () => {
  mockApi({
    "GET /roadmap/gap": { status: 404, body: { detail: "Create your profile before viewing your skill gap" } },
  });
  render(<RoadmapPage />);

  const link = await screen.findByRole("link", { name: "Go to your profile" });
  expect(link).toHaveAttribute("href", "/profile");
});

test("an expired token logs the student out", async () => {
  mockApi({ "GET /roadmap/gap": { status: 401, body: { detail: "Not authenticated" } } });
  render(<RoadmapPage />);

  await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/"));
  expect(getToken()).toBeNull();
});

test("a non-student account is told the page is for students", async () => {
  mockApi({ "GET /roadmap/gap": { status: 403, body: { detail: "Only students have a skill gap" } } });
  render(<RoadmapPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent("This page is for student accounts.");
});

test("an unreachable server shows an error", async () => {
  global.fetch = jest.fn().mockRejectedValue(new Error("network down"));
  render(<RoadmapPage />);

  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the server");
});

test("log out clears the token", async () => {
  mockApi({ "GET /roadmap/gap": { status: 200, body: GAP } });
  render(<RoadmapPage />);
  await screen.findByText("Target role: Backend Developer");

  await userEvent.setup().click(screen.getByRole("button", { name: "Log out" }));

  expect(getToken()).toBeNull();
  expect(mockReplace).toHaveBeenCalledWith("/");
});
