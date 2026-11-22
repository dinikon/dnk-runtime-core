import { feedApi } from "../api/feed.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type { ArchiveFeed } from "./feed.types";
export function useArchiveFeed(): FeedAction<ArchiveFeed, void> {
  return useFeedAction(feedApi.archive);
}
