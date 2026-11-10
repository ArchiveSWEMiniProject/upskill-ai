import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CompleteResource } from "@/app/(m3)/progress/CompleteResource";
import type { ProgressRecord } from "@/lib/progress";
import { mockApi } from "@/test-utils/api";

const record: ProgressRecord = {
  progress_id: 5, resource_id: 12, status: "in-progress", completion_percentage: 60,
};

test("completion displays the accepted server record, never an optimistic completion", async () => {
  const completed = { ...record, status: "completed", completion_percentage: 100 };
  const calls = mockApi({ "POST /progress/5/complete": { status: 200, body: completed } });
  const onCompleted = jest.fn();
  render(<CompleteResource progress={record} onCompleted={onCompleted} />);
  await userEvent.click(screen.getByRole("button", { name: "Mark complete" }));
  expect(onCompleted).toHaveBeenCalledWith(completed);
  expect(calls.at(-1)?.body).toEqual({});
});

test.each([
  [409, "Submit valid completion evidence before completing this resource."],
  [503, "Completion is unavailable until this resource's evidence requirements are confirmed."],
])("%s keeps progress unchanged and shows the evidence message", async (status, detail) => {
  mockApi({ "POST /progress/5/complete": { status: Number(status), body: { detail } } });
  const onCompleted = jest.fn();
  render(<CompleteResource progress={record} onCompleted={onCompleted} />);
  await userEvent.click(screen.getByRole("button", { name: "Mark complete" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(String(detail));
  expect(onCompleted).not.toHaveBeenCalled();
});

test("a completed resource has no repeated completion control", () => {
  render(<CompleteResource progress={{ ...record, status: "completed", completion_percentage: 100 }}
    onCompleted={jest.fn()} />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

test("submits a numeric quiz score when adding evidence after self-reported completion", async () => {
  const completed: ProgressRecord = { ...record, status: "completed", completion_percentage: 100 };
  const calls = mockApi({ "POST /progress/5/complete": { status: 200, body: completed } });
  render(<CompleteResource progress={completed} onCompleted={jest.fn()} />);
  await userEvent.selectOptions(screen.getByRole("combobox"), "quiz");
  await userEvent.type(screen.getByLabelText("Quiz score (0–100)"), "0");
  await userEvent.click(screen.getByRole("button", { name: "Save evidence" }));
  expect(calls.at(-1)?.body).toEqual({ evidence: { evidence_type: "quiz", score: 0 } });
  expect(await screen.findByText("Completion evidence saved.")).toBeInTheDocument();
});
