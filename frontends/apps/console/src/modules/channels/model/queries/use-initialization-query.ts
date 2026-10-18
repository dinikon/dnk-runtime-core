import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { Initialization } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function useInitializationQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
  poll: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<Initialization, ChannelsApiError> {
  return useQuery<Initialization, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.initialization(ctx.scope.value, toValue(id)),
    ),
    queryFn: ({ signal }) => channelsApi.initialization(toValue(id), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(id)),
    retry: false,
    refetchIntervalInBackground: false,
    refetchInterval: computed(() => (toValue(poll) ? 2000 : false)),
  });
}
