import { feedApi } from "../api/feed.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type { FeedSettings, Feed } from "./feed.types";
export function useCreateFeed(): FeedAction<FeedSettings, Feed> {
  return useFeedAction(feedApi.create);
}
