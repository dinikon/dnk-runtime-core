import { type UseMutationReturnType, useMutation } from "@tanstack/vue-query";
import { channelsApi } from "../../api/channels.api";
import type { ChannelsApiError } from "../../api/channels.error";
import type {
  StartInitializationInput,
  InitializationQueued,
} from "../channels.types";
import type { ChannelsContext } from "../use-channels-context";
export function useStartInitialization(
  ctx: ChannelsContext,
): UseMutationReturnType<
  InitializationQueued,
  ChannelsApiError,
  StartInitializationInput,
  string
> {
  return useMutation<
    InitializationQueued,
    ChannelsApiError,
    StartInitializationInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => channelsApi.startInitialization(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _variables, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
