import { httpClient } from "@/app/providers/http";
import { feedRequest } from "./feed-request";
import { mapFeedExport, mapFeedExportIssues } from "./feed-export.mapper";
import type {
  FeedExportIssuesDTO,
  FeedExportStateDTO,
  RequestFeedRefreshDTO,
  RotatedFeedLinkDTO,
} from "./feed-export.dto";
import type {
  ExportIssueSeverity,
  FeedExportAction,
  FeedExportIssues,
  FeedExportState,
  FeedExportTask,
  RotatedFeedLink,
} from "../model/feed-export.types";

function root(id: string): string {
  return `/console/feed-builder/feeds/${encodeURIComponent(id)}`;
}
export const feedExportApi = {
  get(id: string, signal: AbortSignal): Promise<FeedExportState> {
    return feedRequest(async () =>
      mapFeedExport(
        (
          await httpClient.get<FeedExportStateDTO>(`${root(id)}/export`, {
            signal,
          })
        ).data,
      ),
    );
  },
  listIssues(
    id: string,
    severity: ExportIssueSeverity | "",
    offset: number,
    signal: AbortSignal,
  ): Promise<FeedExportIssues> {
    return feedRequest(async () =>
      mapFeedExportIssues(
        (
          await httpClient.get<FeedExportIssuesDTO>(
            `${root(id)}/export/issues`,
            {
              signal,
              params: { severity: severity || undefined, offset, limit: 25 },
            },
          )
        ).data,
      ),
    );
  },
  refresh(
    action: FeedExportAction,
    signal: AbortSignal,
  ): Promise<FeedExportTask> {
    return feedRequest(async () => {
      const { data } = await httpClient.post<RequestFeedRefreshDTO>(
        `${root(action.feedId)}/export/refresh`,
        { expected_version: action.version },
        { signal },
      );
      return {
        status: data.status,
        requestedAt: data.requested_at,
        startedAt: null,
      };
    });
  },
  rotate(
    action: FeedExportAction,
    signal: AbortSignal,
  ): Promise<RotatedFeedLink> {
    return feedRequest(async () => {
      const { data } = await httpClient.post<RotatedFeedLinkDTO>(
        `${root(action.feedId)}/public-link/rotate`,
        { expected_version: action.version },
        { signal },
      );
      return { url: data.url, feedVersion: data.feed_version };
    });
  },
};
