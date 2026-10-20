import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { publicationImportApi } from "../../api/publication-import.api";
import type { StartPublicationImportInput } from "../publication-import.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useStartPublicationImport(
  ctx: ChannelsContext,
): UseMutationReturnType<
  string,
  ChannelsApiError,
  StartPublicationImportInput,
  string
> {
  return useMutation<
    string,
    ChannelsApiError,
    StartPublicationImportInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => publicationImportApi.start(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
