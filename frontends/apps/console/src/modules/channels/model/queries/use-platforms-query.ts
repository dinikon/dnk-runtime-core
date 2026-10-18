import { computed } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { Platform } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function usePlatformsQuery(
  ctx: ChannelsContext,
): UseQueryReturnType<Platform[], ChannelsApiError> {
  return useQuery<Platform[], ChannelsApiError>({
    queryKey: computed(() => channelsKeys.platforms(ctx.scope.value)),
    queryFn: ({ signal }) => channelsApi.platforms(signal),
    enabled: ctx.enabled,
    retry: false,
    refetchIntervalInBackground: false,
  });
}
