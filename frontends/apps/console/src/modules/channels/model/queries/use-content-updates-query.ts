import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { contentUpdatesApi } from "../../api/content-updates.api";
import type { ContentUpdateSummary } from "../content-update.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
import { channelsKeys } from "../channels.query-keys";
export function useContentUpdatesQuery(
  ctx: ChannelsContext,
  channelId: MaybeRefOrGetter<string>,
): UseQueryReturnType<ContentUpdateSummary[], ChannelsApiError> {
  return useQuery<ContentUpdateSummary[], ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.contentUpdates(ctx.scope.value, toValue(channelId)),
    ),
    queryFn: ({ signal }) =>
      contentUpdatesApi.recent(toValue(channelId), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(channelId)),
    retry: false,
    refetchOnWindowFocus: true,
  });
}
