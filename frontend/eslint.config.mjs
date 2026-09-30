import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { globalIgnores } from "eslint/config";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });
const eslintConfig = [
  globalIgnores([".next/**", "node_modules/**", "coverage/**", "next-env.d.ts", "jest.config.cjs"]),
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
