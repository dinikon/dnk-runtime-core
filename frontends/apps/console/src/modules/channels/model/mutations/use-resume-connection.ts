import { type UseMutationReturnType, useMutation } from "@tanstack/vue-query";
import { channelsApi } from "../../api/channels.api";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelRevisionInput } from "../channels.types";
import type { ChannelsContext } from "../use-channels-context";
export function useResumeConnection(
  ctx: ChannelsContext,
): UseMutationReturnType<void, ChannelsApiError, ChannelRevisionInput, string> {
  return useMutation<void, ChannelsApiError, ChannelRevisionInput, string>({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => channelsApi.resume(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _variables, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
