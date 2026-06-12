import { httpClient } from "@/app/providers/http";

import type {
  BroadcastFieldsResponse,
  BroadcastResponse,
  CreateBroadcastPayload,
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
  list: async (payload: ListBroadcastsPayload) =>
    (
      await httpClient.post<ListBroadcastsResponse>(
        "/console/broadcast/broadcast/item/list",
        payload,
      )
    ).data,
};
