import nextConfig from "eslint-config-next";
import pluginSecurity from "eslint-plugin-security";

const next = Array.isArray(nextConfig) ? nextConfig : [nextConfig];

/** @type {import("eslint").Linter.FlatConfig[]} */
const eslintConfig = [
  {
    ignores: [".next/**", "coverage/**", "node_modules/**", "out/**", "dist/**"],
  },
  ...next,
  pluginSecurity.configs.recommended,
  {
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    files: ["**/*.test.ts", "**/*.test.tsx"],
    rules: {
      "react/display-name": "off",
    },
  },
];

export default eslintConfig;
