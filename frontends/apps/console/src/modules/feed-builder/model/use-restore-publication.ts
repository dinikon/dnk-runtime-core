import { feedPublicationApi } from "../api/feed-publication.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type {
  PublicationVersionAction,
  ChangedPublication,
} from "./feed-publication.types";
export function useRestorePublication(): FeedAction<
  PublicationVersionAction,
  ChangedPublication
> {
  return useFeedAction(feedPublicationApi.restore);
}
