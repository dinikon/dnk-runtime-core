import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { contentUpdatesApi } from "../../api/content-updates.api";
import type { ContentUpdate } from "../content-update.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
import { channelsKeys } from "../channels.query-keys";
import { contentUpdateActive } from "../content-update.presentation";
export function useContentUpdateQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
  enabled: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<ContentUpdate, ChannelsApiError> {
  return useQuery<ContentUpdate, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.contentUpdate(ctx.scope.value, toValue(id)),
    ),
    queryFn: ({ signal }) => contentUpdatesApi.get(toValue(id), signal),
    enabled: computed(
      () => ctx.enabled.value && !!toValue(id) && toValue(enabled),
    ),
    refetchInterval: (query) =>
      query.state.error
        ? false
        : contentUpdateActive(query.state.data)
          ? 1000
          : false,
    refetchOnWindowFocus: true,
    retry: false,
  });
}
