import { httpClient } from "@/app/providers/http";
import { normalizeApiError } from "./channels.error";
import {
  mapContentUpdate,
  mapContentUpdateHistory,
  contentUpdateStartPayload,
  contentUpdateConfirmPayload,
} from "./content-updates.mapper";
import type * as DTO from "./content-updates.dto";
import type * as Model from "../model/content-update.types";
const path = (id: string): string =>
  `/console/channels/content-updates/${encodeURIComponent(id)}`;
export const contentUpdatesApi = {
  async start(
    input: Model.StartContentUpdateInput,
    signal?: AbortSignal,
  ): Promise<string> {
    try {
      const { data } = await httpClient.post<DTO.StartContentUpdateResponseDto>(
        `/console/channels/${encodeURIComponent(input.channelId)}/content-updates`,
        contentUpdateStartPayload(input),
        { signal },
      );
      return data.run_id;
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async get(id: string, signal?: AbortSignal): Promise<Model.ContentUpdate> {
    try {
      const { data } = await httpClient.get<DTO.GetContentUpdateResponseDto>(
        path(id),
        { signal },
      );
      return mapContentUpdate(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async recent(
    channelId: string,
    signal?: AbortSignal,
  ): Promise<Model.ContentUpdateSummary[]> {
    try {
      const { data } = await httpClient.get<DTO.ListContentUpdatesResponseDto>(
        `/console/channels/${encodeURIComponent(channelId)}/content-updates`,
        { signal },
      );
      return mapContentUpdateHistory(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async confirm(
    input: Model.ConfirmContentUpdateInput,
    signal?: AbortSignal,
  ): Promise<string> {
    try {
      const { data } =
        await httpClient.post<DTO.ConfirmContentUpdateResponseDto>(
          path(input.runId) + "/confirm",
          contentUpdateConfirmPayload(input),
          { signal },
        );
      return data.run_id;
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async retry(
    input: Model.RetryContentUpdateInput,
    signal?: AbortSignal,
  ): Promise<string> {
    const payload: DTO.RetryContentUpdateRequestDto = {
      expected_revision: input.revision,
    };
    try {
      const { data } = await httpClient.post<DTO.RetryContentUpdateResponseDto>(
        path(input.runId) + "/retry",
        payload,
        { signal },
      );
      return data.run_id;
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async setOutbound(
    input: Model.SetOutboundInput,
    signal?: AbortSignal,
  ): Promise<void> {
    const payload: DTO.SetOutboundRequestDto = {
      revision: input.revision,
      is_enabled: input.enabled,
    };
    try {
      await httpClient.patch<DTO.SetOutboundResponseDto>(
        `/console/channels/${encodeURIComponent(input.channelId)}`,
        payload,
        { signal },
      );
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
};
