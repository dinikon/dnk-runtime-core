import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { contentUpdatesApi } from "../../api/content-updates.api";
import type { SetOutboundInput } from "../content-update.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useSetOutbound(
  ctx: ChannelsContext,
): UseMutationReturnType<void, ChannelsApiError, SetOutboundInput, string> {
  return useMutation<void, ChannelsApiError, SetOutboundInput, string>({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => contentUpdatesApi.setOutbound(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
