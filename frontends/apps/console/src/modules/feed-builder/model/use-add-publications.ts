import { feedPublicationApi } from "../api/feed-publication.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type {
  AddPublications,
  AddedPublications,
} from "./feed-publication.types";
export function useAddPublications(): FeedAction<
  AddPublications,
  AddedPublications
> {
  return useFeedAction(feedPublicationApi.add);
}
