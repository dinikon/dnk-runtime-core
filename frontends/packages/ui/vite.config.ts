import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  base: "/static/core/ui/",
  build: {
    manifest: "manifest.json",
    outDir: fileURLToPath(new URL("../../../core/src/accounts/static/core/ui", import.meta.url)),
    emptyOutDir: true,
    rollupOptions: { input: fileURLToPath(new URL("./src/django/main.ts", import.meta.url)) },
  },
});
