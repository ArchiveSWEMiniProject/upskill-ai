import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { MAX_BYTES, ResumeSection, retentionText, type Upload } from "@/app/(m1)/_components/ResumeSection";
import { setToken } from "@/lib/api";
import { mockApi } from "@/test-utils/api";
import { FakeUpload, installFakeUpload } from "@/test-utils/xhr";

const onUnauthorized = jest.fn();

const READ: Upload = {
  upload_id: 9,
  file_name: "asha-cv.pdf",
  file_type: "pdf",
  size_bytes: 48_213,
  status: "extracted",
  message: null,
  uploaded_at: "2026-10-28T10:00:00Z",
  delete_after: "2026-11-27T10:00:00Z",
  deleted: false,
};

function pdf(name = "asha-cv.pdf", bytes = 1024) {
  return new File([new Uint8Array(bytes)], name, { type: "application/pdf" });
}

async function renderSection(uploads: Upload[] = []) {
  mockApi({ "GET /profile/resume": { status: 200, body: uploads } });
  installFakeUpload();
  render(<ResumeSection onUnauthorized={onUnauthorized} />);
  await screen.findByRole("form", { name: "Upload a resume" });
}

async function choose(file: File) {
  const user = userEvent.setup({ applyAccept: false });
  await user.upload(screen.getByLabelText("Resume file"), file);
  await user.click(screen.getByRole("button", { name: "Upload resume" }));
}

test("the processing indicator follows the upload, then the result is shown", async () => {
  setToken("signed.jwt.token");
  await renderSection();
  await choose(pdf());

  const request = FakeUpload.last!;
  expect(request.method).toBe("POST");
  expect(request.url).toBe("/api/v1/profile/resume");
  expect(request.headers.Authorization).toBe("Bearer signed.jwt.token");
  expect((request.body!.get("file") as File).name).toBe("asha-cv.pdf");

  const status = screen.getByRole("status");
  expect(within(status).getByText("Uploading… 0%")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Upload resume" })).toBeDisabled();

  act(() => request.progress(512, 1024));
  expect(within(status).getByRole("progressbar", { name: "Upload progress" })).toHaveAttribute("value", "50");
  expect(within(status).getByText("Uploading… 50%")).toBeInTheDocument();

  act(() => request.sent());
  expect(within(status).getByRole("progressbar", { name: "Processing" })).toBeInTheDocument();
  expect(within(status).getByText("Processing your resume…")).toBeInTheDocument();

  await act(async () => request.respond(201, READ));
  expect(within(status).queryByRole("progressbar")).not.toBeInTheDocument();
  expect(within(status).getByText("asha-cv.pdf was read successfully.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Upload resume" })).toBeEnabled();
  expect(screen.getByRole("list", { name: "Your uploads" })).toHaveTextContent("asha-cv.pdf");
});

test("a file over 5 MB is refused with the exact message, without uploading it", async () => {
  await renderSection();
  await choose(pdf("large_resume.pdf", MAX_BYTES + 1));
  expect(screen.getByRole("alert")).toHaveTextContent(/^File exceeds the 5 MB limit\.$/);
  expect(FakeUpload.last).toBeNull();
});

test("the API's exact message is shown for a file that is not PDF or DOCX", async () => {
  await renderSection();
  await choose(new File(["plain text"], "resume_sample.txt", { type: "text/plain" }));
  await act(async () =>
    FakeUpload.last!.respond(415, { detail: "Only PDF and DOCX files are accepted." }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent(/^Only PDF and DOCX files are accepted\.$/);
  expect(screen.queryByRole("list", { name: "Your uploads" })).not.toBeInTheDocument();
});

test("an unreadable resume says so and points to manual entry", async () => {
  await renderSection();
  await choose(pdf("scanned_only.pdf"));
  const message = "We could not read any text in this resume. You can add your skills manually instead.";
  await act(async () =>
    FakeUpload.last!.respond(201, { ...READ, file_name: "scanned_only.pdf", status: "unreadable", message, deleted: true }),
  );
  expect(screen.getByRole("alert")).toHaveTextContent(message);
  expect(screen.getByRole("list", { name: "Your uploads" })).toHaveTextContent(
    "scanned_only.pdfNo readable text",
  );
});

test("earlier uploads show when their file is or was deleted", async () => {
  await renderSection([READ, { ...READ, upload_id: 3, file_name: "old.docx", deleted: true }]);
  const list = await screen.findByRole("list", { name: "Your uploads" });
  expect(list).toHaveTextContent("asha-cv.pdfRead successfully · uploaded 28 Oct 2026 · File deleted on 27 Nov 2026");
  expect(list).toHaveTextContent("old.docxRead successfully · uploaded 28 Oct 2026 · File deleted");
});

test("retention text", () => {
  expect(retentionText(READ)).toBe("File deleted on 27 Nov 2026");
  expect(retentionText({ ...READ, deleted: true })).toBe("File deleted");
});

test("an expired token is handed to the page", async () => {
  await renderSection();
  await choose(pdf());
  await act(async () => FakeUpload.last!.respond(401, { detail: "Not authenticated" }));
  expect(onUnauthorized).toHaveBeenCalledWith(401);
});

test("a dropped connection is reported", async () => {
  await renderSection();
  await choose(pdf());
  await act(async () => FakeUpload.last!.onerror!());
  expect(screen.getByRole("alert")).toHaveTextContent("Cannot reach the server");
  expect(screen.getByRole("button", { name: "Upload resume" })).toBeEnabled();
});
