import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery } from "@tanstack/vue-query";

import { broadcastApi } from "@/modules/broadcast/api";
import { broadcastQueryKeys } from "@/modules/broadcast/model/broadcast.query-keys";

export function useBroadcastQuery(
  id: MaybeRefOrGetter<string>,
  enabled: MaybeRefOrGetter<boolean> = true,
) {
  return useQuery({
    queryKey: computed(() => broadcastQueryKeys.detail(toValue(id))),
    queryFn: () => broadcastApi.get({ id: toValue(id) }),
    enabled: computed(() => toValue(enabled)),
    retry: false,
  });
}
