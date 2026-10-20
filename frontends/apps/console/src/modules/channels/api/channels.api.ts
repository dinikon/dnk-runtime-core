import { normalizeApiError } from "./channels.error";
import { httpClient } from "@/app/providers/http";
import type * as DTO from "./channels.dto";
import * as map from "./channels.mapper";
import type * as Model from "../model/channels.types";
const root = "/console/channels";
const channelPath = (id: string): string => `${root}/${encodeURIComponent(id)}`;
const connectionPath = (id: string): string =>
  `${root}/connections/${encodeURIComponent(id)}`;
export const channelsApi = {
  async platforms(signal?: AbortSignal): Promise<Model.Platform[]> {
    try {
      const { data } = await httpClient.get<DTO.ListPlatformsResponseDto>(
        `${root}/platforms`,
        { signal },
      );
      return data.items.map(map.mapPlatform);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async platform(kind: string, signal?: AbortSignal): Promise<Model.Platform> {
    try {
      const { data } = await httpClient.get<DTO.GetPlatformConfigResponseDto>(
        `${root}/platforms/${encodeURIComponent(kind)}/config`,
        { signal },
      );
      return map.mapPlatform(data.manifest);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async list(
    filters: Model.ChannelsFilters,
    signal?: AbortSignal,
  ): Promise<Model.ChannelsPage> {
    try {
      const { data } = await httpClient.get<DTO.ListChannelsResponseDto>(root, {
        params: filters,
        signal,
      });
      return { items: data.items.map(map.mapChannel), total: data.total };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async get(id: string, signal?: AbortSignal): Promise<Model.Channel> {
    try {
      const { data } = await httpClient.get<DTO.GetChannelResponseDto>(
        channelPath(id),
        { signal },
      );
      return map.mapChannel(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async create(
    input: Model.CreateChannelInput,
    signal?: AbortSignal,
  ): Promise<Model.CreatedChannel> {
    try {
      const { data } = await httpClient.post<DTO.CreateChannelResponseDto>(
        root,
        map.createChannelPayload(input),
        { signal },
      );
      return map.mapCreatedChannel(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async connection(
    id: string,
    signal?: AbortSignal,
  ): Promise<Model.Connection> {
    try {
      const { data } = await httpClient.get<DTO.GetConnectionResponseDto>(
        `${channelPath(id)}/connection`,
        { signal },
      );
      return map.mapConnection(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async createConnection(
    input: Model.CreateConnectionInput,
    signal?: AbortSignal,
  ): Promise<Model.ConnectionSaved> {
    try {
      const { data } = await httpClient.post<DTO.CreateConnectionResponseDto>(
        `${channelPath(input.channelId)}/connection`,
        map.createConnectionPayload(input),
        { signal },
      );
      return map.mapConnectionSaved(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async updateConnection(
    input: Model.UpdateConnectionInput,
    signal?: AbortSignal,
  ): Promise<Model.ConnectionSaved> {
    try {
      const { data } = await httpClient.patch<DTO.UpdateConnectionResponseDto>(
        `${channelPath(input.channelId)}/connection`,
        map.updateConnectionPayload(input),
        { signal },
      );
      return map.mapConnectionSaved(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async verify(
    input: Model.ChannelRevisionInput,
    signal?: AbortSignal,
  ): Promise<Model.VerificationQueued> {
    try {
      const payload: DTO.VerifyConnectionRequestDto = {
        revision: input.revision,
      };
      const { data } = await httpClient.post<DTO.VerifyConnectionResponseDto>(
        `${channelPath(input.channelId)}/connection/verify`,
        payload,
        { signal },
      );
      return map.mapVerification(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async pause(
    input: Model.ChannelRevisionInput,
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      const payload: DTO.PauseConnectionRequestDto = {
        revision: input.revision,
      };
      await httpClient.post(
        `${channelPath(input.channelId)}/connection/pause`,
        payload,
        { signal },
      );
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async resume(
    input: Model.ChannelRevisionInput,
    signal?: AbortSignal,
  ): Promise<void> {
    try {
      const payload: DTO.ResumeConnectionRequestDto = {
        revision: input.revision,
      };
      await httpClient.post(
        `${channelPath(input.channelId)}/connection/resume`,
        payload,
        { signal },
      );
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async initialization(
    id: string,
    signal?: AbortSignal,
  ): Promise<Model.Initialization> {
    try {
      const { data } = await httpClient.get<DTO.GetInitializationResponseDto>(
        `${connectionPath(id)}/initialization`,
        { signal },
      );
      return map.mapInitialization(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async startInitialization(
    input: Model.StartInitializationInput,
    signal?: AbortSignal,
  ): Promise<Model.InitializationQueued> {
    try {
      const payload: DTO.StartInitializationRequestDto = {
        request_key: input.requestKey,
      };
      const { data } =
        await httpClient.post<DTO.StartInitializationResponseDto>(
          `${connectionPath(input.connectionId)}/initialization`,
          payload,
          { signal },
        );
      return map.mapInitializationQueued(data);
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async publications(
    id: string,
    filters: Model.PublicationsFilters,
    signal?: AbortSignal,
  ): Promise<Model.PublicationsPage> {
    try {
      const { data } = await httpClient.get<DTO.ListPublicationsResponseDto>(
        `${connectionPath(id)}/publications`,
        {
          params: {
            offset: filters.offset,
            limit: filters.limit,
            search: filters.search || undefined,
            stock_status: filters.stockStatus || undefined,
            binding_status: filters.bindingStatus || undefined,
            identity_status: filters.identityStatus || undefined,
            identity_key: filters.identityKey || undefined,
          },
          signal,
        },
      );
      return {
        items: data.items.map(map.mapPublication),
        total: data.total,
        identitySummary: map.mapIdentitySummary(data.identity_summary),
      };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
  async references(signal?: AbortSignal): Promise<Model.ConnectionReferences> {
    try {
      const [locales, currencies] = await Promise.all([
        httpClient.get<DTO.ReferenceOptionDto[]>(
          "/console/reference-data/locales",
          { signal },
        ),
        httpClient.get<DTO.ReferenceOptionDto[]>(
          "/console/reference-data/currencies",
          { signal },
        ),
      ]);
      return {
        locales: locales.data.map(({ code, name }) => ({ code, name })),
        currencies: currencies.data.map(({ code, name }) => ({ code, name })),
      };
    } catch (error: unknown) {
      throw normalizeApiError(error);
    }
  },
};
