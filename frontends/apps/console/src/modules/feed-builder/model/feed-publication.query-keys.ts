import type { FeedScope } from "./feed.query-keys.ts";
import type { PublicationFilters } from "./feed-publication.types.ts";
import { feedKeys } from "./feed.query-keys.ts";
type Key = readonly unknown[];
export const publicationKeys = {
  locales: (scope: FeedScope) => [...feedKeys.root(scope), "publication-locales"] as const,
  fields: (scope: FeedScope, feedId: string, publicationId: string) =>
    [
      ...feedKeys.root(scope),
      "publication-fields",
      feedId,
      publicationId,
    ] as const,
  listScope: (scope: FeedScope, feedId: string): Key => [
    ...feedKeys.root(scope),
    "publications",
    feedId,
  ],
  detailScope: (scope: FeedScope, publicationId: string): Key => [
    ...feedKeys.root(scope),
    "publication",
    publicationId,
  ],
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
