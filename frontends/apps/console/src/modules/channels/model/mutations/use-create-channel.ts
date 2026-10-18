import { type UseMutationReturnType, useMutation } from "@tanstack/vue-query";
import { channelsApi } from "../../api/channels.api";
import type { ChannelsApiError } from "../../api/channels.error";
import type { CreateChannelInput, CreatedChannel } from "../channels.types";
import type { ChannelsContext } from "../use-channels-context";
export function useCreateChannel(
  ctx: ChannelsContext,
): UseMutationReturnType<
  CreatedChannel,
  ChannelsApiError,
  CreateChannelInput,
  string
> {
  return useMutation<
    CreatedChannel,
    ChannelsApiError,
    CreateChannelInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => channelsApi.create(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _variables, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
