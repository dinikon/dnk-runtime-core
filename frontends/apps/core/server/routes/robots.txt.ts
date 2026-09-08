import { defineEventHandler, setHeader } from "h3";
import { useRuntimeConfig } from "nitropack/runtime";

export default defineEventHandler((event) => {
  setHeader(event, "Content-Type", "text/plain; charset=utf-8");
  const sitemap = new URL("/sitemap.xml", useRuntimeConfig(event).public.siteUrl).href;
  return `User-agent: *\nAllow: /\nDisallow: /app\nDisallow: /accounts/\nDisallow: /api/\nDisallow: /admin/\nSitemap: ${sitemap}\n`;
});
