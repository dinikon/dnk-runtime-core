import { feedApi } from "../api/feed.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type { UpdateFeed, Feed } from "./feed.types";
export function useUpdateFeed(): FeedAction<UpdateFeed, Feed> {
  return useFeedAction(feedApi.update);
}
