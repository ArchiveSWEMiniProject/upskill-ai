import { errorMessage, fieldErrors, formJson } from "@/lib/forms";

test("422 details become one message per field, without pydantic's prefix", () => {
  const detail = [
    { loc: ["body", "email"], msg: "Value error, Enter a valid email address" },
    { loc: ["body", "email"], msg: "second message is ignored" },
    { loc: ["body", "password"], msg: "String should have at least 8 characters" },
  ];
  expect(fieldErrors(detail)).toEqual({
    email: "Enter a valid email address",
    password: "String should have at least 8 characters",
  });
});

test("anything that is not a 422 list gives no field errors", () => {
  expect(fieldErrors("Profile not found")).toEqual({});
  expect(fieldErrors(undefined)).toEqual({});
  expect(fieldErrors([{ msg: "no location" }])).toEqual({});
});

test("the error message comes from a string detail or a detail object", () => {
  expect(errorMessage({ detail: "Invalid email or password" })).toBe("Invalid email or password");
  expect(errorMessage({ detail: { message: "Unknown skill: Pythn" } })).toBe("Unknown skill: Pythn");
  expect(errorMessage(null, "fallback")).toBe("fallback");
});

test("form values are trimmed and blank optional fields become null", () => {
  const entries: [string, string][] = [
    ["name", "  Asha  "],
    ["education_level", "   "],
    ["course_code", ""],
  ];
  expect(formJson(entries, ["education_level"])).toEqual({
    name: "Asha",
    education_level: null,
    course_code: "",
  });
});
