import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    watch: {
      ignored: [
        "**/artifacts/**",
        "**/playwright-report/**",
        "**/test-results/**"
      ],
    },
    port: 5173,
    strictPort: true,
    fs: {
      deny: ["artifacts"],       // don't serve artifacts
    },
  },
});
