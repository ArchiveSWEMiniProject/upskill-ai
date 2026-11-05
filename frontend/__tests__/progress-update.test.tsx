import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProgressUpdate } from "@/app/(m3)/progress/ProgressUpdate";
import type { ProgressRecord } from "@/lib/progress";
import { mockApi } from "@/test-utils/api";

const record: ProgressRecord = {
  progress_id: 5, resource_id: 12, status: "enrolled", completion_percentage: 0,
};

test("saves the percentage to the enrolled progress ID (TC-F3-03)", async () => {
  const updated = { ...record, status: "in-progress", completion_percentage: 60 };
  const calls = mockApi({ "PATCH /progress/5": { status: 200, body: updated } });
  const onUpdated = jest.fn();
  render(<ProgressUpdate progress={record} onUpdated={onUpdated} />);
  const input = screen.getByRole("spinbutton");
  await userEvent.clear(input); await userEvent.type(input, "60");
  await userEvent.click(screen.getByRole("button", { name: "Save progress" }));
  expect(onUpdated).toHaveBeenCalledWith(updated);
  expect(calls.at(-1)?.body).toEqual({ completion_percentage: 60 });
});

test("server validation identifies the field and does not replace stored progress (TC-F3-04)", async () => {
  mockApi({ "PATCH /progress/5": { status: 422, body: { detail: [
    { loc: ["body", "completion_percentage"], msg: "Input should be less than or equal to 100" },
  ] } } });
  const onUpdated = jest.fn();
  render(<ProgressUpdate progress={record} onUpdated={onUpdated} />);
  await userEvent.clear(screen.getByRole("spinbutton"));
  await userEvent.type(screen.getByRole("spinbutton"), "140");
  await userEvent.click(screen.getByRole("button", { name: "Save progress" }));
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  expect(screen.getByRole("spinbutton")).toHaveAttribute("aria-invalid", "true");
  expect(onUpdated).not.toHaveBeenCalled();
});

test("an empty value is not silently saved as zero", async () => {
  const calls = mockApi({});
  render(<ProgressUpdate progress={record} onUpdated={jest.fn()} />);
  await userEvent.clear(screen.getByRole("spinbutton"));
  await userEvent.click(screen.getByRole("button", { name: "Save progress" }));
  expect(screen.getByRole("spinbutton")).toHaveAccessibleDescription("Enter a completion percentage.");
  expect(calls).toHaveLength(0);
});

test("completed records have no percentage editor", () => {
  render(<ProgressUpdate progress={{ ...record, status: "completed", completion_percentage: 100 }}
    onUpdated={jest.fn()} />);
  expect(screen.queryByRole("form")).not.toBeInTheDocument();
});
