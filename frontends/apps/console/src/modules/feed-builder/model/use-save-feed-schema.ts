import { feedSchemaApi } from "../api/feed-schema.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type { SaveFeedSchema, SavedFeedSchema } from "./feed-schema.types";
export function useSaveFeedSchema(): FeedAction<
  SaveFeedSchema,
  SavedFeedSchema
> {
  return useFeedAction(feedSchemaApi.save);
}
