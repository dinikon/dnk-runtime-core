import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { contentUpdatesApi } from "../../api/content-updates.api";
import type { RetryContentUpdateInput } from "../content-update.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useRetryContentUpdate(
  ctx: ChannelsContext,
): UseMutationReturnType<
  string,
  ChannelsApiError,
  RetryContentUpdateInput,
  string
> {
  return useMutation<string, ChannelsApiError, RetryContentUpdateInput, string>(
    {
      gcTime: 0,
      retry: false,
      mutationFn: (input) => contentUpdatesApi.retry(input, ctx.signal()),
      onMutate: () => ctx.scope.value,
      onSettled: async (_data, _error, _input, scope) => {
        if (scope) await ctx.refresh(scope);
      },
    },
  );
}
