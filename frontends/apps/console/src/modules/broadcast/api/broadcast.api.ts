import { httpClient } from "@/app/providers/http";

import type {
  BroadcastFieldsResponse,
  BroadcastResponse,
  CreateBroadcastPayload,
  GetBroadcastPayload,
  ListBroadcastsPayload,
  ListBroadcastsResponse,
} from "./types";

export const broadcastApi = {
  create: async (payload: CreateBroadcastPayload) =>
    (
      await httpClient.post<BroadcastResponse>(
        "/console/broadcast/item/add",
        payload,
      )
    ).data,
  describeFields: async () =>
    (
      await httpClient.post<BroadcastFieldsResponse>(
        "/console/broadcast/broadcast/item/fields",
      )
    ).data,
  get: async (payload: GetBroadcastPayload) =>
    (
      await httpClient.post<BroadcastResponse>(
        "/console/broadcast/broadcast/item/get",
        payload,
      )
    ).data,
  list: async (payload: ListBroadcastsPayload) =>
    (
      await httpClient.post<ListBroadcastsResponse>(
        "/console/broadcast/broadcast/item/list",
        payload,
      )
    ).data,
};
