import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { type UseQueryReturnType, useQuery } from "@tanstack/vue-query";
import type { Channel } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function useChannelQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
): UseQueryReturnType<Channel, ChannelsApiError> {
  return useQuery<Channel, ChannelsApiError>({
    queryKey: computed(() => channelsKeys.detail(ctx.scope.value, toValue(id))),
    queryFn: ({ signal }) => channelsApi.get(toValue(id), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(id)),
    retry: false,
    refetchIntervalInBackground: false,
  });
}
