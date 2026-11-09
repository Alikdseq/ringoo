import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      react: path.resolve(__dirname, "node_modules/react"),
      "react-dom": path.resolve(__dirname, "node_modules/react-dom"),
      "react/jsx-runtime": path.resolve(
        __dirname,
        "node_modules/react/jsx-runtime.js"
      ),
    },
    dedupe: ["react", "react-dom"],
  },
  test: {
    // Контейнер frontend часто с NODE_ENV=production — тогда React.act отсутствует.
    env: {
      NODE_ENV: "test",
    },
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    server: {
      deps: {
        inline: ["@testing-library/react", "@testing-library/dom", "react-dom"],
      },
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      include: [
        "src/components/**/*.{ts,tsx}",
        "src/lib/hooks/**/*.ts",
        "src/lib/theme/utils.ts",
        "src/lib/utils/**/*.ts",
        "src/lib/image-url.ts",
      ],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.d.ts",
        "src/test/**",
      ],
      thresholds: {
        lines: 30,
        functions: 30,
        branches: 30,
        statements: 30,
      },
    },
  },
});

