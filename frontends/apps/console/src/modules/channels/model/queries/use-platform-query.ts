import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { Platform } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function usePlatformQuery(
  ctx: ChannelsContext,
  kind: MaybeRefOrGetter<string>,
): UseQueryReturnType<Platform, ChannelsApiError> {
  return useQuery<Platform, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.platform(ctx.scope.value, toValue(kind)),
    ),
    queryFn: ({ signal }) => channelsApi.platform(toValue(kind), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(kind)),
    retry: false,
    refetchIntervalInBackground: false,
  });
}
