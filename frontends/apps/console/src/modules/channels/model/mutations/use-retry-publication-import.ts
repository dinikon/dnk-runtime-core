import { useMutation, type UseMutationReturnType } from "@tanstack/vue-query";
import { publicationImportApi } from "../../api/publication-import.api";
import type {
  ChangePublicationImportInput,
  ChangedPublicationImport,
} from "../publication-import.types";
import type { ChannelsApiError } from "../../api/channels.error";
import type { ChannelsContext } from "../use-channels-context";
export function useRetryPublicationImport(
  ctx: ChannelsContext,
): UseMutationReturnType<
  ChangedPublicationImport,
  ChannelsApiError,
  ChangePublicationImportInput,
  string
> {
  return useMutation<
    ChangedPublicationImport,
    ChannelsApiError,
    ChangePublicationImportInput,
    string
  >({
    gcTime: 0,
    retry: false,
    mutationFn: (input) => publicationImportApi.retry(input, ctx.signal()),
    onMutate: () => ctx.scope.value,
    onSettled: async (_data, _error, _input, scope) => {
      if (scope) await ctx.refresh(scope);
    },
  });
}
