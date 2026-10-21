import { httpClient } from "@/app/providers/http";
import { normalizeApiError } from "./channels.error";
import type * as DTO from "./batch-export.dto";
import type * as Model from "../model/batch-export.types";
import {
  mapBatchOverview,
  mapBatchDetail,
  schedulePayload,
  publicationExportPayload,
} from "./batch-export.mapper";
const channelPath = (id: string): string =>
  `/console/channels/${encodeURIComponent(id)}`;
export const batchExportApi = {
  async overview(
    id: string,
    signal?: AbortSignal,
  ): Promise<Model.BatchExportOverview> {
    try {
      const { data } = await httpClient.get<DTO.BatchExportOverviewDto>(
        channelPath(id) + "/batch-export",
        { signal },
      );
      return mapBatchOverview(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async get(
    input: Model.BatchExportPageInput,
    signal?: AbortSignal,
  ): Promise<Model.BatchExportDetail> {
    try {
      const { data } = await httpClient.get<DTO.BatchExportDetailDto>(
        `/console/channels/batch-exports/${encodeURIComponent(input.runId)}`,
        { params: { offset: input.offset, limit: input.limit }, signal },
      );
      return mapBatchDetail(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async start(
    input: Model.StartBatchExportInput,
    signal?: AbortSignal,
  ): Promise<string> {
    const payload: DTO.StartBatchExportRequestDto = {
      run_id: input.runId,
      delivery_mode: input.deliveryMode,
    };
    try {
      const { data } = await httpClient.post<DTO.StartBatchExportResponseDto>(
        channelPath(input.channelId) + "/batch-exports",
        payload,
        { signal },
      );
      return data.run_id;
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async schedule(
    input: Model.ExportScheduleInput,
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      await httpClient.put<DTO.UpdateExportScheduleResponseDto>(
        channelPath(input.channelId) + "/export-schedule",
        schedulePayload(input),
        { signal },
      );
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async setExport(
    input: Model.SetPublicationExportInput,
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      await httpClient.patch<DTO.SetPublicationExportResponseDto>(
        channelPath(input.channelId) + "/publication-export",
        publicationExportPayload(input),
        { signal },
      );
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async resume(id: string, signal?: AbortSignal): Promise<void> {
    try {
      await httpClient.post<DTO.StartBatchExportResponseDto>(
        `/console/channels/batch-exports/${encodeURIComponent(id)}/resume`,
        {},
        { signal },
      );
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
};
