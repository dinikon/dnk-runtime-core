import { feedPublicationApi } from "../api/feed-publication.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type { PublicationVersionAction } from "./feed-publication.types";
export function useArchivePublication(): FeedAction<
  PublicationVersionAction,
  void
> {
  return useFeedAction(feedPublicationApi.archive);
}
