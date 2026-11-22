import { isAxiosError } from "axios";
import { httpClient } from "@/app/providers/http";
import {
  FeedPreviewError,
  type FeedPreview,
  type FeedPreviewRequest,
} from "../model/feed-preview.types";
import type { FeedPreviewDTO, FeedPreviewErrorDTO } from "./feed-preview.dto";
import { mapFeedPreview, mapTestCsvIssue } from "./feed-preview.mapper";

const root = "/console/feed-builder/feeds";

async function asPreviewError(error: unknown): Promise<unknown> {
  if (!isAxiosError<FeedPreviewErrorDTO | Blob>(error) || !error.response)
    return error;
  const { status, data } = error.response;
  let payload: FeedPreviewErrorDTO | undefined;
  try {
    payload =
      data instanceof Blob
        ? (JSON.parse(await data.text()) as FeedPreviewErrorDTO)
        : data;
  } catch {
    payload = undefined;
  }
  const detail = payload?.detail;
  const message = typeof detail === "string" ? detail : detail?.message;
  const issues =
    typeof detail === "object" && Array.isArray(detail?.issues)
      ? detail.issues.map(mapTestCsvIssue)
      : [];
  return new FeedPreviewError(
    message ?? "Не удалось выполнить запрос.",
    status,
    issues,
  );
}

export const feedPreviewApi = {
  async preview(
    input: FeedPreviewRequest,
    signal: AbortSignal,
  ): Promise<FeedPreview> {
    try {
      const response = await httpClient.post<FeedPreviewDTO>(
        `${root}/${encodeURIComponent(input.feedId)}/preview`,
        { expected_version: input.expectedVersion },
        { signal },
      );
      return mapFeedPreview(response.data);
    } catch (error: unknown) {
      throw await asPreviewError(error);
    }
  },
  async download(
    input: FeedPreviewRequest,
    signal: AbortSignal,
  ): Promise<Blob> {
    try {
      const response = await httpClient.post<Blob>(
        `${root}/${encodeURIComponent(input.feedId)}/test-csv`,
        { expected_version: input.expectedVersion },
        { responseType: "blob", signal },
      );
      return response.data;
    } catch (error: unknown) {
      throw await asPreviewError(error);
    }
  },
};
