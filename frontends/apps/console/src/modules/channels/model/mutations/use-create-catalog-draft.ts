import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { catalogLinksApi } from "../../api/catalog-links.api";
import type {
  CreateDraftInput,
  CreatedCatalogDraft,
} from "../catalog-links.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useCreateCatalogDraft(
  ctx: ChannelsContext,
): UseMutationReturnType<
  CreatedCatalogDraft,
  ChannelsApiError,
  CreateDraftInput,
  string
> {
  return useMutation<
    CreatedCatalogDraft,
    ChannelsApiError,
    CreateDraftInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => catalogLinksApi.createDraft(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
