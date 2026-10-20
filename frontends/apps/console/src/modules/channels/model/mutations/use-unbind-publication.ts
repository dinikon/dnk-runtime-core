import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { catalogLinksApi } from "../../api/catalog-links.api";
import type { UnbindPublicationInput } from "../catalog-links.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useUnbindPublication(
  ctx: ChannelsContext,
): UseMutationReturnType<
  void,
  ChannelsApiError,
  UnbindPublicationInput,
  string
> {
  return useMutation<void, ChannelsApiError, UnbindPublicationInput, string>({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => catalogLinksApi.unbind(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
