/// <reference types="vitest/config" />
import { defineConfig } from "vite";

export default defineConfig({
  // Default "/" is correct for custom-domain hosting and for local dev/preview.
  // Set VITE_BASE to "/<repo-name>/" when hosting on a GitHub Pages project site.
  base: process.env.VITE_BASE ?? "/",
  test: {
    environment: "jsdom",
    include: ["tests/**/*.test.ts"],
  },
});
