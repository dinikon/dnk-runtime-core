import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { batchExportApi } from "../../api/batch-export.api";
import type { StartBatchExportInput } from "../batch-export.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useStartBatchExport(
  ctx: ChannelsContext,
): UseMutationReturnType<
  string,
  ChannelsApiError,
  StartBatchExportInput,
  string
> {
  return useMutation<string, ChannelsApiError, StartBatchExportInput, string>({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => batchExportApi.start(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
