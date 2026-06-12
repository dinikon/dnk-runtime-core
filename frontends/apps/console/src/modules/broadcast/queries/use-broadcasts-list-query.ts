import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery } from "@tanstack/vue-query";

import {
  broadcastApi,
  type ListBroadcastsPayload,
} from "@/modules/broadcast/api";
import { broadcastQueryKeys } from "@/modules/broadcast/model/broadcast.query-keys";

export function useBroadcastsListQuery(
  payload: MaybeRefOrGetter<ListBroadcastsPayload>,
  enabled: MaybeRefOrGetter<boolean> = true,
) {
  return useQuery({
    queryKey: computed(() => broadcastQueryKeys.list(toValue(payload))),
    queryFn: () => broadcastApi.list(toValue(payload)),
    enabled: computed(() => toValue(enabled)),
    retry: false,
  });
}
