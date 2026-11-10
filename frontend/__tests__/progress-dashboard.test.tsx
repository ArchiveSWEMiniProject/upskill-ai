import { render, screen } from "@testing-library/react";
import ProgressDashboardPage from "@/app/(m3)/progress/dashboard/page";
import { mockApi } from "@/test-utils/api";

test("shows enrolled progress and keeps missing gap data distinct from zero", async () => {
  mockApi({ "GET /progress/dashboard": {
    status: 200,
    body: {
      completed_count: 1, current_streak_days: 2,
      gap_summary: null, gap_closure_proportion: null,
      milestones: [{ label: "First resource completed", achieved_at: null }],
      resources: [{
        resource_id: 4, progress_id: 2, title: "Testing course",
        status: "completed", completion_percentage: 100, history: [],
      }],
    },
  } });
  render(<ProgressDashboardPage />);
  expect(await screen.findByRole("link", { name: "Testing course" })).toHaveAttribute("href", "/progress/4");
  expect(screen.getByText("completed · 100% complete")).toBeInTheDocument();
  expect(screen.getByText("First resource completed")).toBeInTheDocument();
  expect(screen.getByText("Gap summary unavailable")).toBeInTheDocument();
});
