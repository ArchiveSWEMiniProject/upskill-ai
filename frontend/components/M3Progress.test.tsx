import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import M3Progress from "./M3Progress";

const emptyDashboard = {
  enrolments: [], completed_count: 0, active_count: 0, progress_percent: 0,
  milestones: [], gaps_closed: null, total_gaps: null,
  gaps_status: "pending-m2-integration", streak_days: null,
  streak_status: "criteria-not-defined-in-source-documents",
};

function response(body: unknown) {
  return Promise.resolve({ ok: true, json: async () => body } as Response);
}

describe("M3 progress screen", () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue(response(emptyDashboard));
  });

  it("labels the temporary identity integration clearly", () => {
    render(<M3Progress />);
    expect(screen.getByText(/Temporary development identity field/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enrol" })).toBeInTheDocument();
  });

  it("sends an enrolment to the M3 API with the current student context", async () => {
    render(<M3Progress />);
    fireEvent.change(screen.getByLabelText("Student ID"), { target: { value: "S-01" } });
    fireEvent.change(screen.getByLabelText("Learning resource ID"), {
      target: { value: "LI-1001" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enrol" }));

    await waitFor(() => {
      const call = (global.fetch as jest.Mock).mock.calls.find(
        ([url, init]) => String(url).endsWith("/progress/enrolments") && init.method === "POST",
      );
      expect(call).toBeDefined();
      expect(JSON.parse(call[1].body)).toEqual({ resource_id: "LI-1001" });
      expect(call[1].headers.get("X-Student-Id")).toBe("S-01");
    });
  });
});
