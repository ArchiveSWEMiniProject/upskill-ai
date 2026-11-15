import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResourceProgress } from "@/app/(m3)/progress/ResourceProgress";
import { mockApi } from "@/test-utils/api";

const resource = { item_id: 12, title: "Testing course", source_url: "https://example.org/course" };
const initial = { progress_id: 5, resource_id: 12, status: "enrolled", completion_percentage: 0 };

test("enrol sends the resource identity and displays the stored initial state", async () => {
  const calls = mockApi({
    "GET /catalogue/12": { status: 200, body: resource },
    "POST /progress/enrol": { status: 201, body: initial },
  });
  render(<ResourceProgress resourceId={12} />);
  await userEvent.click(await screen.findByRole("button", { name: "Enrol / resume tracking" }));
  expect(await screen.findByRole("status")).toHaveTextContent("enrolled: 0% complete");
  expect(calls.at(-1)?.body).toEqual({ resource_id: 12 });
});

test("a failed enrolment displays the server error and allows retry", async () => {
  mockApi({
    "GET /catalogue/12": { status: 200, body: resource },
    "POST /progress/enrol": { status: 404, body: { detail: "Approved resource not found" } },
  });
  render(<ResourceProgress resourceId={12} />);
  await userEvent.click(await screen.findByRole("button", { name: "Enrol / resume tracking" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Approved resource not found");
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

test("an unavailable resource cannot be enrolled", async () => {
  mockApi({ "GET /catalogue/12": { status: 404, body: { detail: "Resource not found" } } });
  render(<ResourceProgress resourceId={12} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Resource not found");
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
