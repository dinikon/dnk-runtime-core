import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { batchExportApi } from "../../api/batch-export.api";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useResumeBatchExport(
  ctx: ChannelsContext,
): UseMutationReturnType<void, ChannelsApiError, string, string> {
  return useMutation<void, ChannelsApiError, string, string>({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => batchExportApi.resume(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
