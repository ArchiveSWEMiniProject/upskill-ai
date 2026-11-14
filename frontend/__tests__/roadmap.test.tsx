import { render, screen, within } from "@testing-library/react";

import RoadmapPage from "@/app/(m2)/roadmap/page";
import { setToken } from "@/lib/api";
import { mockApi } from "@/test-utils/api";

// Next's useRouter returns the same object on every render; so must the mock.
const mockRouter = { push: jest.fn(), replace: jest.fn() };
jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));

const ROADMAP = {
  role_id: 3,
  role_name: "Backend Developer",
  items: [
    {
      rank: 1, skill_id: 1, skill_name: "Python",
      required_level: "intermediate", current_level: "beginner", weight: 5,
      resources: [
        {
          item_id: 11, title: "Python Tutorial", item_type: "course",
          coverage_level: "intermediate", duration: "10 hours", source: "python.org",
          source_url: "https://docs.python.org/3/tutorial/",
        },
        {
          item_id: 12, title: "PCEP certification", item_type: "certification",
          coverage_level: "intermediate", duration: null, source: null,
          source_url: "https://pythoninstitute.org/pcep",
        },
      ],
    },
    {
      rank: 2, skill_id: 4, skill_name: "Docker",
      required_level: "beginner", current_level: null, weight: 1,
      resources: [],
    },
  ],
};

beforeEach(() => setToken("signed.jwt.token"));

test("the roadmap is requested from GET /roadmap", async () => {
  const calls = mockApi({ "GET /roadmap": { status: 200, body: ROADMAP } });
  render(<RoadmapPage />);

  await screen.findByRole("group", { name: "Resources for Python" });
  expect(calls[0].path).toBe("/roadmap");
});

test("each gap skill lists its resources as links with type, level and duration", async () => {
  mockApi({ "GET /roadmap": { status: 200, body: ROADMAP } });
  render(<RoadmapPage />);

  const python = await screen.findByRole("group", { name: "Resources for Python" });
  const tutorial = within(python).getByRole("link", { name: "Python Tutorial" });
  expect(tutorial).toHaveAttribute("href", "https://docs.python.org/3/tutorial/");
  expect(tutorial).toHaveAttribute("target", "_blank");
  expect(tutorial).toHaveAttribute("rel", expect.stringContaining("noopener"));
  expect(python).toHaveTextContent("Course - Intermediate - 10 hours - python.org");
  expect(within(python).getByRole("link", { name: "PCEP certification" })).toBeInTheDocument();
  expect(python).toHaveTextContent("Certification - Intermediate");
});

test("a gap skill with no resources says so instead of showing an empty space", async () => {
  mockApi({ "GET /roadmap": { status: 200, body: ROADMAP } });
  render(<RoadmapPage />);

  const docker = await screen.findByRole("group", { name: "Resources for Docker" });
  expect(docker).toHaveTextContent("No catalogue resources for this skill yet.");
  expect(within(docker).queryByRole("link")).not.toBeInTheDocument();
});
