import { defineConfig } from "vite";

// The website chat widget (phase 4): one self-contained file, no React, served by the API at
// /chat/widget.js. Built after the portal into dist/widget/ (the portal build empties dist).
export default defineConfig({
  build: {
    outDir: "dist/widget",
    emptyOutDir: true,
    lib: {
      entry: "src/widget/main.ts",
      name: "QuotationChat",
      formats: ["iife"],
      fileName: () => "widget.js",
    },
  },
});
