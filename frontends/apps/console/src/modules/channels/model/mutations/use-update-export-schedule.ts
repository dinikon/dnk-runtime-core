import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { batchExportApi } from "../../api/batch-export.api";
import type { ExportScheduleInput } from "../batch-export.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useUpdateExportSchedule(
  ctx: ChannelsContext,
): UseMutationReturnType<void, ChannelsApiError, ExportScheduleInput, string> {
  return useMutation<void, ChannelsApiError, ExportScheduleInput, string>({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => batchExportApi.schedule(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
