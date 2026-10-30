import { httpClient } from "@/app/providers/http";
import { channelRequest } from "./channel.api";
import {
  mapContentFeed,
  mapFeedPreview,
  mapFeedImport,
  feedImportRevision,
  requestFeedImportPayload,
  attachFeedImportPayload,
  resolveFeedImportPayload,
  createContentFeedPayload,
  saveContentFeedPayload,
  contentFeedRevisionPayload,
} from "./content-feed.mapper";
import type {
  ContentFeedDto,
  FeedPreviewDto,
  FeedImportDto,
} from "./content-feed.dto";
import type {
  ContentFeed,
  FeedPreview,
  FeedImport,
  FeedLocation,
  CreateFeedInput,
  SaveFeedInput,
  FeedRevisionInput,
  FeedImportRevisionInput,
  RequestFeedImportInput,
  AttachFeedImportInput,
  ResolveFeedImportInput,
} from "../model/content-feed.types";

const root = (channelId: string): string =>
  `/console/channels/${encodeURIComponent(channelId)}/content-feeds`;
const item = (input: FeedLocation): string =>
  `${root(input.channelId)}/${encodeURIComponent(input.feedId)}`;
export async function getContentFeeds(
  channelId: string,
  signal?: AbortSignal,
): Promise<ContentFeed[]> {
  return channelRequest(async () =>
    (
      await httpClient.get<{ items: ContentFeedDto[] }>(root(channelId), {
        signal,
      })
    ).data.items.map(mapContentFeed),
  );
}
export async function createContentFeed(
  input: CreateFeedInput,
): Promise<ContentFeed> {
  return channelRequest(async () =>
    mapContentFeed(
      (
        await httpClient.post<{ feed: ContentFeedDto }>(
          root(input.channelId),
          createContentFeedPayload(input),
        )
      ).data.feed,
    ),
  );
}
export async function saveContentFeed(
  input: SaveFeedInput,
): Promise<ContentFeed> {
  return channelRequest(async () =>
    mapContentFeed(
      (
        await httpClient.put<{ feed: ContentFeedDto }>(
          item(input),
          saveContentFeedPayload(input),
        )
      ).data.feed,
    ),
  );
}
export async function previewContentFeed(
  input: FeedLocation,
): Promise<FeedPreview> {
  return channelRequest(async () =>
    mapFeedPreview(
      (await httpClient.post<FeedPreviewDto>(item(input) + "/preview")).data,
    ),
  );
}
export async function enableContentFeed(
  input: FeedRevisionInput,
): Promise<ContentFeed> {
  return channelRequest(async () =>
    mapContentFeed(
      (
        await httpClient.post<{ feed: ContentFeedDto }>(
          item(input) + "/enable",
          contentFeedRevisionPayload(input),
        )
      ).data.feed,
    ),
  );
}
export async function disableContentFeed(
  input: FeedRevisionInput,
): Promise<ContentFeed> {
  return channelRequest(async () =>
    mapContentFeed(
      (
        await httpClient.post<{ feed: ContentFeedDto }>(
          item(input) + "/disable",
          contentFeedRevisionPayload(input),
        )
      ).data.feed,
    ),
  );
}
export async function getFeedImport(
  input: FeedLocation,
  signal?: AbortSignal,
): Promise<FeedImport> {
  return channelRequest(async () =>
    mapFeedImport(
      (
        await httpClient.get<{ operation: FeedImportDto }>(
          item(input) + "/imports/current",
          { signal },
        )
      ).data.operation,
    ),
  );
}
export async function requestFeedImport(
  input: RequestFeedImportInput,
): Promise<FeedImport> {
  return channelRequest(async () =>
    mapFeedImport(
      (
        await httpClient.post<{ operation: FeedImportDto }>(
          item(input) + "/imports",
          requestFeedImportPayload(input),
        )
      ).data.operation,
    ),
  );
}
export async function resumeFeedImport(
  input: FeedImportRevisionInput,
): Promise<FeedImport> {
  return channelRequest(async () =>
    mapFeedImport(
      (
        await httpClient.post<{ operation: FeedImportDto }>(
          item(input) + "/imports/current/resume",
          feedImportRevision(input),
        )
      ).data.operation,
    ),
  );
}
export async function attachFeedImport(
  input: AttachFeedImportInput,
): Promise<FeedImport> {
  return channelRequest(async () =>
    mapFeedImport(
      (
        await httpClient.post<{ operation: FeedImportDto }>(
          item(input) + "/imports/current/attach",
          attachFeedImportPayload(input),
        )
      ).data.operation,
    ),
  );
}
export async function resolveFeedImport(
  input: ResolveFeedImportInput,
): Promise<FeedImport> {
  return channelRequest(async () =>
    mapFeedImport(
      (
        await httpClient.post<{ operation: FeedImportDto }>(
          item(input) + "/imports/current/resolve",
          resolveFeedImportPayload(input),
        )
      ).data.operation,
    ),
  );
}
