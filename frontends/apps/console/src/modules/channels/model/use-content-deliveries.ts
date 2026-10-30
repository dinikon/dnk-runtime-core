import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getContentDeliveries } from "../api/content-delivery.api";
import { useChannelScope } from "./use-channel-scope";
import { contentDeliveryKeys } from "./content-delivery.query-keys";
import type { ContentDelivery } from "./content-delivery.types";

export function useContentDeliveries(
  channelId: Ref<string>,
  groupId: Ref<string>,
  enabled: Ref<boolean>,
): UseQueryReturnType<ContentDelivery[], Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      contentDeliveryKeys.detail(scope.value, channelId.value, groupId.value),
    ),
    queryFn: ({ signal }) =>
      getContentDeliveries(channelId.value, groupId.value, signal),
    enabled: computed(
      () =>
        enabled.value &&
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!channelId.value &&
        !!groupId.value,
    ),
    refetchInterval: (query) =>
      query.state.data?.some(
        (item) =>
          !item.recoveryRequired &&
          ["queued", "in_flight", "unknown"].includes(item.status),
      )
        ? 2000
        : false,
    retry: false,
  });
}
