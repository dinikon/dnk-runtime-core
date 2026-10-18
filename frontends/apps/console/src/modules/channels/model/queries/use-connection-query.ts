import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { Connection } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function useConnectionQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
  enabled: MaybeRefOrGetter<boolean>,
  poll: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<Connection, ChannelsApiError> {
  return useQuery<Connection, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.connection(ctx.scope.value, toValue(id)),
    ),
    queryFn: ({ signal }) => channelsApi.connection(toValue(id), signal),
    enabled: computed(() => ctx.enabled.value && toValue(enabled)),
    retry: false,
    refetchIntervalInBackground: false,
    refetchInterval: computed(() => (toValue(poll) ? 2000 : false)),
  });
}
