import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { contentUpdatesApi } from "../../api/content-updates.api";
import type { StartContentUpdateInput } from "../content-update.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useStartContentUpdate(
  ctx: ChannelsContext,
): UseMutationReturnType<
  string,
  ChannelsApiError,
  StartContentUpdateInput,
  string
> {
  return useMutation<string, ChannelsApiError, StartContentUpdateInput, string>(
    {
      gcTime: 0,
      retry: false,
      mutationFn: (input) => contentUpdatesApi.start(input, ctx.signal()),
      onMutate: () => ctx.scope.value,
      onSettled: async (_data, _error, _input, scope) => {
        if (scope) await ctx.refresh(scope);
      },
    },
  );
}
