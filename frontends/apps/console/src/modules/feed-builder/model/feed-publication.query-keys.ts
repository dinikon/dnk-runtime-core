import type { FeedScope } from "./feed.query-keys.ts";
import type { PublicationFilters } from "./feed-publication.types.ts";
type Key = readonly unknown[];
export const publicationKeys = {
  list: (s: FeedScope, id: string, f: PublicationFilters): Key => [
    "feed-builder",
    ...s,
    "publications",
    id,
    f,
  ],
  detail: (s: FeedScope, id: string, locale: string): Key => [
    "feed-builder",
    ...s,
    "publication",
    id,
    locale,
  ],
  products: (
    s: FeedScope,
    locale: string,
    search: string,
    offset: number,
  ): Key => [
    "feed-builder",
    ...s,
    "publication-products",
    locale,
    search,
    offset,
  ],
  variants: (
    s: FeedScope,
    rootId: string,
    locale: string,
    offset: number,
  ): Key => [
    "feed-builder",
    ...s,
    "publication-variants",
    rootId,
    locale,
    offset,
  ],
};
