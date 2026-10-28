import type { PublicationFilters } from "./publication.types";

export const publicationPageSizes = [25, 50, 100];

export function parsePublicationFilters(
  query: Record<string, unknown>,
): PublicationFilters {
  const requestedLimit =
    typeof query.limit === "string" ? Number(query.limit) : NaN;
  const limit = publicationPageSizes.includes(requestedLimit)
    ? requestedLimit
    : 25;
  const requestedOffset =
    typeof query.offset === "string" ? Number(query.offset) : 0;
  const offset = Number.isFinite(requestedOffset)
    ? Math.min(2147483600, Math.max(0, Math.floor(requestedOffset)))
    : 0;
  return {
    search: typeof query.q === "string" ? query.q : "",
    locale: typeof query.locale === "string" ? query.locale : "",
    limit,
    offset: Math.floor(offset / limit) * limit,
  };
}

export function publicationPaginationQuery(value: {
  page: number;
  limit: number;
}): { limit: string | undefined; offset: string | undefined } {
  const limit = publicationPageSizes.includes(value.limit) ? value.limit : 25;
  const page = Number.isFinite(value.page)
    ? Math.max(1, Math.floor(value.page))
    : 1;
  const offset = Math.min(2147483600, (page - 1) * limit);
  return {
    limit: limit === 25 ? undefined : String(limit),
    offset: offset ? String(offset) : undefined,
  };
}
