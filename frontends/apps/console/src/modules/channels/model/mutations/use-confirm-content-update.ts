import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { contentUpdatesApi } from "../../api/content-updates.api";
import type { ConfirmContentUpdateInput } from "../content-update.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useConfirmContentUpdate(
  ctx: ChannelsContext,
): UseMutationReturnType<
  string,
  ChannelsApiError,
  ConfirmContentUpdateInput,
  string
> {
  return useMutation<
    string,
    ChannelsApiError,
    ConfirmContentUpdateInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => contentUpdatesApi.confirm(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
