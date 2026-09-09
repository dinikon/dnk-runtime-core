import tailwindcss from "@tailwindcss/vite";
import { defineNuxtConfig } from "nuxt/config";

const backend = process.env.CORE_PROXY_TARGET ?? "http://127.0.0.1:8001";

export default defineNuxtConfig({
  compatibilityDate: "2026-09-08",
  srcDir: "src",
  ssr: true,
  devtools: { enabled: false },
  css: ["@dnk/ui/style.css", "~/style.css"],
  vite: { plugins: [tailwindcss()] },
  build: { transpile: ["@dnk/ui"] },
  runtimeConfig: {
    public: { siteUrl: "http://localhost:8080" },
  },
  app: {
    head: {
      htmlAttrs: { lang: "ru" },
      meta: [{ name: "theme-color", content: "#ffffff" }],
      link: [
        { rel: "icon", type: "image/svg+xml", href: "/static/core/favicon.svg" },
        { rel: "stylesheet", href: "/static/core/theme.css" },
      ],
    },
  },
  routeRules: {
    "/": { headers: { "Cache-Control": "no-cache" } },
    "/app": { headers: { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" } },
    "/app/**": { headers: { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex, nofollow" } },
  },
  nitro: {
    preset: "node-server",
    devProxy: Object.fromEntries(
      ["/api", "/accounts", "/admin", "/static"].map((path) => [path, { target: `${backend}${path}`, changeOrigin: false }]),
    ),
  },
  typescript: { strict: true },
});
