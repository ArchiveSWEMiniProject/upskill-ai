import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ExtractedSkillsSection } from "@/app/(m1)/_components/ExtractedSkillsSection";
import { setToken } from "@/lib/api";
import { mockApi } from "@/test-utils/api";

const skill = (candidate_id: number, skill_name: string, confidence: number, level = "beginner") => ({
  candidate_id,
  upload_id: 3,
  skill_id: candidate_id + 100,
  skill_name,
  suggested_level: level,
  confidence,
  source_sentence: `Skills: ${skill_name}`,
  status: "pending",
});
const PYTHON = skill(1, "Python", 0.9);
const DOCKER = skill(2, "Docker", 0.6, "intermediate");
const listing = (...candidates: unknown[]) => ({ status: 200, body: { threshold: 0.8, candidates } });

beforeEach(() => setToken("signed.jwt.token"));

function show() {
  render(<ExtractedSkillsSection refreshKey={0} onUnauthorized={jest.fn()} />);
}

test("each found skill is shown with its confidence and source sentence", async () => {
  mockApi({ "GET /profile/resume/extracted": listing(PYTHON, DOCKER) });
  show();
  const list = await screen.findByRole("list", { name: "Skills to review" });
  const items = within(list).getAllByRole("listitem");
  expect(items[0]).toHaveTextContent("Python");
  expect(items[0]).toHaveTextContent("90% confidence");
  expect(items[0]).toHaveTextContent("Skills: Python");
  expect(within(items[1]).getByRole("combobox", { name: "Level for Docker" })).toHaveValue(
    "intermediate",
  );
});

test("nothing is shown when there is nothing to review", async () => {
  const calls = mockApi({ "GET /profile/resume/extracted": listing() });
  show();
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(calls).toHaveLength(1);
  expect(screen.queryByRole("heading")).not.toBeInTheDocument();
});

test("confirming at an edited level sends that level and refreshes the list", async () => {
  const calls = mockApi({
    "GET /profile/resume/extracted": [listing(PYTHON, DOCKER), listing(DOCKER)],
    "POST /profile/skills/confirm": {
      status: 200,
      body: [{ candidate_id: 1, skill_id: 101, skill_name: "Python", status: "confirmed", level: "advanced" }],
    },
  });
  const user = userEvent.setup();
  show();

  await user.selectOptions(await screen.findByRole("combobox", { name: "Level for Python" }), "advanced");
  await user.click(screen.getByRole("button", { name: "Confirm Python" }));

  expect(await screen.findByText("Added to your profile: Python.")).toBeInTheDocument();
  expect(calls.find((c) => c.method === "POST")?.body).toEqual({
    decisions: [{ candidate_id: 1, action: "confirm", level: "advanced" }],
  });
  expect(screen.queryByRole("button", { name: "Confirm Python" })).not.toBeInTheDocument();
});

test("confirming at the suggested level sends no level, and rejecting works the same way", async () => {
  const calls = mockApi({
    "GET /profile/resume/extracted": listing(PYTHON, DOCKER),
    "POST /profile/skills/confirm": {
      status: 200,
      body: [{ candidate_id: 2, skill_id: 102, skill_name: "Docker", status: "rejected", level: null }],
    },
  });
  const user = userEvent.setup();
  show();

  await user.click(await screen.findByRole("button", { name: "Reject Docker" }));

  expect(await screen.findByText("Rejected: Docker.")).toBeInTheDocument();
  expect(calls.find((c) => c.method === "POST")?.body).toEqual({
    decisions: [{ candidate_id: 2, action: "reject" }],
  });
});

test("bulk confirm is offered only for skills at or above the threshold", async () => {
  const calls = mockApi({
    "GET /profile/resume/extracted": [listing(PYTHON, DOCKER), listing(DOCKER)],
    "POST /profile/skills/confirm-high-confidence": {
      status: 200,
      body: {
        threshold: 0.8,
        confirmed: [{ candidate_id: 1, skill_id: 101, skill_name: "Python", status: "confirmed", level: "beginner" }],
      },
    },
  });
  const user = userEvent.setup();
  show();

  await user.click(await screen.findByRole("button", { name: "Confirm all 1 at 80% confidence or more" }));

  expect(await screen.findByText("Added to your profile: Python.")).toBeInTheDocument();
  expect(calls.some((c) => c.path === "/profile/skills/confirm-high-confidence")).toBe(true);
  expect(screen.queryByRole("button", { name: /Confirm all/ })).not.toBeInTheDocument();
});

test("an error from the API is shown", async () => {
  mockApi({
    "GET /profile/resume/extracted": listing(PYTHON),
    "POST /profile/skills/confirm": {
      status: 409,
      body: { detail: "This extracted skill has already been confirmed or rejected" },
    },
  });
  const user = userEvent.setup();
  show();
  await user.click(await screen.findByRole("button", { name: "Confirm Python" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("already been confirmed or rejected");
});
