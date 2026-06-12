import type { ListBroadcastsPayload } from "@/modules/broadcast/api";

export const broadcastQueryKeys = {
  all: ["broadcast"] as const,
  fields: () => [...broadcastQueryKeys.all, "fields"] as const,
  lists: () => [...broadcastQueryKeys.all, "list"] as const,
  list: (payload: ListBroadcastsPayload) =>
    [...broadcastQueryKeys.lists(), payload] as const,
};
