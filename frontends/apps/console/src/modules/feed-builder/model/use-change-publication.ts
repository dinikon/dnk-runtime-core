import { feedPublicationApi } from "../api/feed-publication.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type {
  ChangePublication,
  ChangedPublication,
} from "./feed-publication.types";
export function useChangePublication(): FeedAction<
  ChangePublication,
  ChangedPublication
> {
  return useFeedAction(feedPublicationApi.change);
}
