import { countCharacters, counterLabel } from "@/lib/characters";

test("characters are counted like the API counts them (code points)", () => {
  expect(countCharacters("")).toBe(0);
  expect(countCharacters("hello")).toBe(5);
  expect(countCharacters("😀")).toBe(1); // two UTF-16 units, one character
  expect(countCharacters("नमस्ते")).toBe(6);
});

test("the label shows the count, and how far over the limit it is", () => {
  expect(counterLabel(1999, 2000)).toBe("1999 / 2000 characters");
  expect(counterLabel(2000, 2000)).toBe("2000 / 2000 characters");
  expect(counterLabel(2050, 2000)).toBe("2050 / 2000 characters, 50 over the limit");
});
