import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { batchExportApi } from "../../api/batch-export.api";
import type { BatchExportOverview } from "../batch-export.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
import { channelsKeys } from "../channels.query-keys";
import { batchPolling } from "../batch-export.presentation";
export function useBatchExportOverviewQuery(
  ctx: ChannelsContext,
  id: MaybeRefOrGetter<string>,
  enabled: MaybeRefOrGetter<boolean>,
): UseQueryReturnType<BatchExportOverview, ChannelsApiError> {
  return useQuery<BatchExportOverview, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.batchOverview(ctx.scope.value, toValue(id)),
    ),
    queryFn: ({ signal }) => batchExportApi.overview(toValue(id), signal),
    enabled: computed(
      () => ctx.enabled.value && !!toValue(id) && toValue(enabled),
    ),
    retry: false,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
    refetchInterval: (query) =>
      query.state.data?.recent.some((run) => batchPolling(run.status))
        ? 3000
        : false,
  });
}
