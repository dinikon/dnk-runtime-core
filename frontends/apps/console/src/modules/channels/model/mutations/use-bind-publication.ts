import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { catalogLinksApi } from "../../api/catalog-links.api";
import type {
  BindPublicationInput,
  BoundPublication,
} from "../catalog-links.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useBindPublication(
  ctx: ChannelsContext,
): UseMutationReturnType<
  BoundPublication,
  ChannelsApiError,
  BindPublicationInput,
  string
> {
  return useMutation<
    BoundPublication,
    ChannelsApiError,
    BindPublicationInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => catalogLinksApi.bind(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
