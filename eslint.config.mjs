import js from "@eslint/js";
import globals from "globals";

export default [
  { ignores: ["node_modules/**", ".cache/**", "outputs/**"] },
  js.configs.recommended,
  {
    files: ["meeting_intelligence/static/**/*.js"],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ["scripts/**/*.mjs", "eslint.config.mjs"],
    languageOptions: { globals: globals.node },
  },
  {
    files: ["scripts/verify_web_ui.mjs"],
    // Playwright evaluate callbacks run in the browser.
    languageOptions: { globals: { document: "readonly", innerWidth: "readonly" } },
  },
];
