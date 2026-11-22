import type { FeedFilters, FeedStatus } from "./feed.types.ts";
const statuses: readonly string[] = ["DRAFT", "ACTIVE", "PAUSED", "ARCHIVED"];
export function feedFilters(query: Record<string, unknown>): FeedFilters {
  const offset =
    typeof query.offset === "string" && /^\d+$/.test(query.offset)
      ? Number(query.offset)
      : 0;
  return {
    search: typeof query.q === "string" ? query.q.slice(0, 255) : "",
    status:
      typeof query.status === "string" && statuses.includes(query.status)
        ? (query.status as FeedStatus)
        : "",
    limit: 50,
    offset: Number.isSafeInteger(offset) ? Math.floor(offset / 50) * 50 : 0,
  };
}
export function feedListReturnTo(value: unknown): string {
  if (typeof value !== "string") return "/feed-builder/feeds";
  try {
    const url = new URL(value, "https://console.invalid");
    return url.origin === "https://console.invalid" &&
      url.pathname === "/feed-builder/feeds"
      ? `${url.pathname}${url.search}${url.hash}`
      : "/feed-builder/feeds";
  } catch {
    return "/feed-builder/feeds";
  }
}
export function lastFeedOffset(total: number, limit: number): number {
  return Math.max(0, Math.ceil(total / limit) - 1) * limit;
}
