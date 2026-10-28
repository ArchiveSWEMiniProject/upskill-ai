import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProjectSection } from "@/app/(m1)/_components/ProjectSection";
import { mockApi } from "@/test-utils/api";

const PROJECT = {
  project_id: 4,
  title: "Study Goals",
  description: "A REST API for tracking study goals.",
  repository_url: "https://github.com/asha/study-goals",
};

const onUnauthorized = jest.fn();

function addForm() {
  return screen.getByRole("form", { name: "Add a project" });
}

function field(form: HTMLElement, label: RegExp) {
  return within(form).getByRole("textbox", { name: label });
}

async function renderEmpty(routes = {}) {
  const calls = mockApi({ "GET /profile/projects": { status: 200, body: [] }, ...routes });
  render(<ProjectSection onUnauthorized={onUnauthorized} />);
  await screen.findByText("No projects yet.");
  return calls;
}

test("the character count updates live while typing", async () => {
  await renderEmpty();
  const description = field(addForm(), /^Description/);
  expect(description).toHaveAccessibleDescription(expect.stringContaining("0 / 2000 characters"));
  await userEvent.setup().type(description, "Built with FastAPI");
  expect(description).toHaveAccessibleDescription(expect.stringContaining("18 / 2000 characters"));
});

test("an over-long description shows its count, and the API's rejection, with nothing added (TC-F1-04)", async () => {
  const calls = await renderEmpty({
    "POST /profile/projects": {
      status: 422,
      body: {
        detail: [
          {
            loc: ["body", "description"],
            msg: "Value error, Description is 2050 characters; the maximum is 2000",
          },
        ],
      },
    },
  });
  const user = userEvent.setup();
  await user.type(field(addForm(), /^Title/), "Test Project");
  await user.click(field(addForm(), /^Description/));
  await user.paste("x".repeat(2050));

  const counter = within(addForm()).getByText("2050 / 2000 characters, 50 over the limit");
  expect(counter).toHaveClass("over-limit");

  await user.click(within(addForm()).getByRole("button", { name: "Add project" }));
  expect(calls.at(-1)?.body.description).toHaveLength(2050);
  const description = field(addForm(), /^Description/);
  expect(description).toHaveAttribute("aria-invalid", "true");
  expect(description).toHaveAccessibleDescription(
    expect.stringContaining("Description is 2050 characters; the maximum is 2000"),
  );
  expect(screen.getByText("No projects yet.")).toBeInTheDocument();
});

test("a project is saved as typed and listed with its repository link", async () => {
  const calls = await renderEmpty({
    "POST /profile/projects": { status: 201, body: PROJECT },
  });
  const user = userEvent.setup();
  await user.type(field(addForm(), /^Title/), " Study Goals ");
  await user.type(field(addForm(), /^Description/), PROJECT.description);
  await user.type(field(addForm(), /^Repository URL/), PROJECT.repository_url);
  await user.click(within(addForm()).getByRole("button", { name: "Add project" }));

  expect(calls.at(-1)?.body).toEqual({
    title: "Study Goals",
    description: PROJECT.description,
    repository_url: PROJECT.repository_url,
  });
  const list = await screen.findByRole("list", { name: "Your projects" });
  expect(within(list).getByRole("link", { name: PROJECT.repository_url })).toHaveAttribute(
    "rel",
    "noopener noreferrer",
  );
  expect(field(addForm(), /^Description/)).toHaveValue("");
  expect(within(addForm()).getByText("0 / 2000 characters")).toBeInTheDocument();
});

test("the repository URL is optional and a malformed one is flagged", async () => {
  const calls = await renderEmpty({
    "POST /profile/projects": {
      status: 422,
      body: {
        detail: [
          { loc: ["body", "repository_url"], msg: "Value error, Repository URL must be a valid http(s) address" },
        ],
      },
    },
  });
  const user = userEvent.setup();
  await user.type(field(addForm(), /^Title/), "Study Goals");
  await user.type(field(addForm(), /^Description/), "Notes");
  await user.click(within(addForm()).getByRole("button", { name: "Add project" }));
  expect(calls.at(-1)?.body.repository_url).toBeNull();

  await user.type(field(addForm(), /^Repository URL/), "github.com/asha/x");
  await user.click(within(addForm()).getByRole("button", { name: "Add project" }));
  expect(field(addForm(), /^Repository URL/)).toHaveAccessibleDescription(
    expect.stringContaining("Repository URL must be a valid http(s) address"),
  );
});

test("editing starts from the saved description and its count", async () => {
  const calls = mockApi({
    "GET /profile/projects": { status: 200, body: [PROJECT] },
    "PUT /profile/projects/4": { status: 200, body: { ...PROJECT, title: "Study Goals API" } },
  });
  const user = userEvent.setup();
  render(<ProjectSection onUnauthorized={onUnauthorized} />);
  await user.click(await screen.findByRole("button", { name: "Edit Study Goals" }));
  const form = screen.getByRole("form", { name: "Edit Study Goals" });
  expect(within(form).getByText(`${PROJECT.description.length} / 2000 characters`)).toBeInTheDocument();

  await user.clear(field(form, /^Title/));
  await user.type(field(form, /^Title/), "Study Goals API");
  await user.click(within(form).getByRole("button", { name: "Save changes" }));
  expect(calls.at(-1)).toMatchObject({ method: "PUT", path: "/profile/projects/4" });
  expect(await screen.findByText("Study Goals API")).toBeInTheDocument();
});

test("deleting asks first", async () => {
  mockApi({
    "GET /profile/projects": { status: 200, body: [PROJECT] },
    "DELETE /profile/projects/4": { status: 204 },
  });
  jest.spyOn(window, "confirm").mockReturnValue(true);
  render(<ProjectSection onUnauthorized={onUnauthorized} />);
  await userEvent.setup().click(await screen.findByRole("button", { name: "Delete Study Goals" }));
  expect(window.confirm).toHaveBeenCalledWith('Delete the project "Study Goals"?');
  expect(await screen.findByText("No projects yet.")).toBeInTheDocument();
});

test("only http(s) repository addresses are rendered as links", async () => {
  mockApi({
    "GET /profile/projects": {
      status: 200,
      body: [{ ...PROJECT, repository_url: "javascript:alert(1)" }],
    },
  });
  render(<ProjectSection onUnauthorized={onUnauthorized} />);
  await screen.findByText("Study Goals");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
