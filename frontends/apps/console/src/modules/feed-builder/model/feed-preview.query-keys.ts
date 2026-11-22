import { feedKeys, type FeedScope } from "./feed.query-keys";

export const feedPreviewKeys = {
  feed: (scope: FeedScope, id: string) =>
    [...feedKeys.root(scope), "preview", id] as const,
  sample: (scope: FeedScope, id: string, version: number | null) =>
    [...feedKeys.root(scope), "preview", id, version] as const,
};
