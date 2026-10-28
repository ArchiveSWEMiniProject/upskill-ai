import nextJest from "next/jest.js";

// next/jest compiles TypeScript and JSX with Next's own SWC setup, so the tests
// see the code exactly as the app build does.
const createJestConfig = nextJest({ dir: "./" });

export default createJestConfig({
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/$1" },
  clearMocks: true,
  testPathIgnorePatterns: ["/node_modules/", "/.next/"],
});
