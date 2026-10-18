import { computed, toValue, type MaybeRefOrGetter } from "vue";
import {
  type UseQueryReturnType,
  useQuery,
  keepPreviousData,
} from "@tanstack/vue-query";
import type { ChannelsPage, ChannelsFilters } from "../channels.types";
import type { ChannelsApiError } from "../../api/channels.error";
import { channelsApi } from "../../api/channels.api";
import { channelsKeys } from "../channels.query-keys";
import type { ChannelsContext } from "../use-channels-context";
export function useChannelsQuery(
  ctx: ChannelsContext,
  filters: MaybeRefOrGetter<ChannelsFilters>,
): UseQueryReturnType<ChannelsPage, ChannelsApiError> {
  return useQuery<ChannelsPage, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.list(ctx.scope.value, toValue(filters)),
    ),
    queryFn: ({ signal }) => channelsApi.list(toValue(filters), signal),
    enabled: ctx.enabled,
    retry: false,
    refetchIntervalInBackground: false,
    placeholderData: keepPreviousData,
  });
}
