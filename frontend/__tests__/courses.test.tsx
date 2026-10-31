import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CourseSection } from "@/app/(m1)/_components/CourseSection";
import { mockApi } from "@/test-utils/api";

const DSA = {
  course_id: 1,
  course_name: "Data Structures",
  course_code: "UE23CS251A",
  grade: "A",
  completion_term: "Sem 3",
};

const onUnauthorized = jest.fn();

function addForm() {
  return screen.getByRole("form", { name: "Add a course" });
}

async function fillCourse(form: HTMLElement, values: Record<string, string>) {
  const user = userEvent.setup();
  for (const [label, value] of Object.entries(values)) {
    const box = within(form).getByRole("textbox", { name: new RegExp(`^${label}`) });
    await user.clear(box);
    if (value) await user.type(box, value);
  }
  await user.click(within(form).getByRole("button", { name: /Add course|Save changes/ }));
}

test("existing courses are listed (TC-F1-02)", async () => {
  mockApi({ "GET /profile/courses": { status: 200, body: [DSA] } });
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  const list = await screen.findByRole("list", { name: "Your courses" });
  expect(list).toHaveTextContent("Data Structures");
  expect(list).toHaveTextContent("UE23CS251A · Grade A · Sem 3");
});

test("a new course is saved and appears in the list (TC-F1-02)", async () => {
  const calls = mockApi({
    "GET /profile/courses": { status: 200, body: [] },
    "POST /profile/courses": { status: 201, body: { ...DSA, course_code: null } },
  });
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  await screen.findByText("No courses yet.");
  await fillCourse(addForm(), {
    "Course name": " Data Structures ",
    Grade: "A",
    "Completion term": "Sem 3",
  });
  expect(calls.at(-1)?.body).toEqual({
    course_name: "Data Structures",
    course_code: null,
    grade: "A",
    completion_term: "Sem 3",
  });
  expect(await screen.findByRole("list", { name: "Your courses" })).toHaveTextContent(
    "Data Structures",
  );
  expect(within(addForm()).getByRole("textbox", { name: /^Course name/ })).toHaveValue("");
});

test("an invalid grade is rejected under the grade field and nothing is added (TC-F1-03)", async () => {
  mockApi({
    "GET /profile/courses": { status: 200, body: [] },
    "POST /profile/courses": {
      status: 422,
      body: {
        detail: [
          {
            loc: ["body", "grade"],
            msg: "Value error, Grade must be one of S, A, B, C, D, E, F or a whole number from 0 to 100",
          },
        ],
      },
    },
  });
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  await screen.findByText("No courses yet.");
  await fillCourse(addForm(), { "Course name": "DBMS", Grade: "Z", "Completion term": "Sem 4" });
  const grade = within(addForm()).getByRole("textbox", { name: /^Grade/ });
  expect(grade).toHaveAttribute("aria-invalid", "true");
  expect(grade).toHaveAccessibleDescription(expect.stringContaining("Grade must be one of S, A"));
  expect(within(addForm()).getByRole("textbox", { name: /^Course name/ })).toHaveAttribute(
    "aria-invalid",
    "false",
  );
  expect(screen.getByText("No courses yet.")).toBeInTheDocument();
});

test("every missing mandatory field is flagged", async () => {
  const missing = (field: string) => ({
    loc: ["body", field],
    msg: "String should have at least 1 character",
  });
  mockApi({
    "GET /profile/courses": { status: 200, body: [] },
    "POST /profile/courses": {
      status: 422,
      body: { detail: [missing("course_name"), missing("grade"), missing("completion_term")] },
    },
  });
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  await screen.findByText("No courses yet.");
  await fillCourse(addForm(), {});
  for (const label of ["Course name", "Grade", "Completion term"]) {
    expect(within(addForm()).getByRole("textbox", { name: new RegExp(`^${label}`) })).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  }
  expect(within(addForm()).getByRole("textbox", { name: /^Course code/ })).toHaveAttribute(
    "aria-invalid",
    "false",
  );
});

test("editing a course replaces it", async () => {
  const calls = mockApi({
    "GET /profile/courses": { status: 200, body: [DSA] },
    "PUT /profile/courses/1": { status: 200, body: { ...DSA, grade: "S" } },
  });
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  await userEvent.setup().click(await screen.findByRole("button", { name: "Edit Data Structures" }));
  await fillCourse(screen.getByRole("form", { name: "Edit Data Structures" }), { Grade: "S" });
  const { course_id, ...fields } = DSA;
  expect(calls.at(-1)).toMatchObject({
    method: "PUT",
    path: `/profile/courses/${course_id}`,
    body: { ...fields, grade: "S" },
  });
  expect(await screen.findByText("UE23CS251A · Grade S · Sem 3")).toBeInTheDocument();
  expect(screen.queryByRole("form", { name: "Edit Data Structures" })).not.toBeInTheDocument();
});

test("deleting asks first, and removes the course only when confirmed", async () => {
  const calls = mockApi({
    "GET /profile/courses": { status: 200, body: [DSA] },
    "DELETE /profile/courses/1": { status: 204 },
  });
  const confirm = jest.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  const user = userEvent.setup();
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  const remove = await screen.findByRole("button", { name: "Delete Data Structures" });

  await user.click(remove);
  expect(calls.some((c) => c.method === "DELETE")).toBe(false);

  await user.click(remove);
  expect(confirm).toHaveBeenCalledWith('Delete the course "Data Structures"?');
  expect(await screen.findByText("No courses yet.")).toBeInTheDocument();
});

test("an expired token is handed to the page", async () => {
  mockApi({ "GET /profile/courses": { status: 401, body: { detail: "Not authenticated" } } });
  render(<CourseSection onUnauthorized={onUnauthorized} />);
  await screen.findByRole("alert");
  expect(onUnauthorized).toHaveBeenCalledWith(401);
});
