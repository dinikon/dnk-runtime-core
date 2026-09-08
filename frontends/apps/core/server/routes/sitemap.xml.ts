import { defineEventHandler, setHeader } from "h3";
import { useRuntimeConfig } from "nitropack/runtime";

export default defineEventHandler((event) => {
  setHeader(event, "Content-Type", "application/xml; charset=utf-8");
  const canonical = new URL("/", useRuntimeConfig(event).public.siteUrl).href.replaceAll("&", "&amp;").replaceAll("<", "&lt;");
  return `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${canonical}</loc></url></urlset>`;
});
