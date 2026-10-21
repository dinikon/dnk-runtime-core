import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { batchExportApi } from "../../api/batch-export.api";
import type {
  BatchExportDetail,
  BatchExportPageInput,
} from "../batch-export.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
import { channelsKeys } from "../channels.query-keys";
import { batchPolling } from "../batch-export.presentation";
export function useBatchExportQuery(
  ctx: ChannelsContext,
  input: MaybeRefOrGetter<BatchExportPageInput>,
): UseQueryReturnType<BatchExportDetail, ChannelsApiError> {
  return useQuery<BatchExportDetail, ChannelsApiError>({
    queryKey: computed(() =>
      channelsKeys.batchDetail(ctx.scope.value, toValue(input)),
    ),
    queryFn: ({ signal }) => batchExportApi.get(toValue(input), signal),
    enabled: computed(() => ctx.enabled.value && !!toValue(input).runId),
    retry: false,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
    refetchInterval: (query) =>
      query.state.data && batchPolling(query.state.data.run.status)
        ? 3000
        : false,
  });
}
