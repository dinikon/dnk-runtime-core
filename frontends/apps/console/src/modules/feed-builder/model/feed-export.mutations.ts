import { feedExportApi } from "../api/feed-export.api";
import { useFeedAction, type FeedAction } from "./use-feed-action";
import type {
  FeedExportAction,
  FeedExportTask,
  RotatedFeedLink,
} from "./feed-export.types";

export function useRequestFeedRefresh(): FeedAction<
  FeedExportAction,
  FeedExportTask
> {
  return useFeedAction(feedExportApi.refresh);
}
export function useRotateFeedLink(): FeedAction<
  FeedExportAction,
  RotatedFeedLink
> {
  return useFeedAction(feedExportApi.rotate);
}
