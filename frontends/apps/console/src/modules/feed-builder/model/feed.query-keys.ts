import type { FeedFilters } from "./feed.types.ts";
export type FeedScope = readonly [string | null, string | null, string];
type FeedRootKey = readonly ["feed-builder", ...FeedScope];
type FeedListKey = readonly [...FeedRootKey, "list", FeedFilters];
type FeedDetailKey = readonly [...FeedRootKey, "detail", string];
export const feedKeys = {
  root: (scope: FeedScope): FeedRootKey => ["feed-builder", ...scope] as const,
  list: (scope: FeedScope, filters: FeedFilters): FeedListKey =>
    [...feedKeys.root(scope), "list", filters] as const,
  detail: (scope: FeedScope, id: string): FeedDetailKey =>
    [...feedKeys.root(scope), "detail", id] as const,
};
