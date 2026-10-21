import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { batchExportApi } from "../../api/batch-export.api";
import type { SetPublicationExportInput } from "../batch-export.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useSetPublicationExport(
  ctx: ChannelsContext,
): UseMutationReturnType<
  void,
  ChannelsApiError,
  SetPublicationExportInput,
  string
> {
  return useMutation<void, ChannelsApiError, SetPublicationExportInput, string>(
    {
      gcTime: 0,
      retry: false,
      mutationFn: (input) => batchExportApi.setExport(input, ctx.signal()),
      onMutate: () => ctx.scope.value,
      onSettled: async (_data, _error, _input, scope) => {
        if (scope) await ctx.refresh(scope);
      },
    },
  );
}
