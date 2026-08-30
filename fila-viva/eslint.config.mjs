import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Script CommonJS puro, roda via `node` no postinstall antes de
    // qualquer coisa do app existir — de propósito fora do mundo TS/ESM
    // do resto do projeto.
    "scripts/setup-env.cjs",
  ]),
]);

export default eslintConfig;
