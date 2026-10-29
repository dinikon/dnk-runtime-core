import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import type { CreatePublicationCatalogResult } from "./catalog-creation.types";
import { useChannelScope } from "./use-channel-scope";
import {
  channelKeys,
  publicationCatalogMutationKey,
  type ChannelScope,
} from "./channel.query-keys";
import { createPublicationCatalog } from "../api/catalog-creation.api";
export function useCreatePublicationCatalog(): UseMutationReturnType<
  CreatePublicationCatalogResult,
  Error,
  { channelId: string; publicationId: string },
  ChannelScope
> {
  const scope = useChannelScope(),
    cache = useQueryClient();
  return useMutation({
    mutationKey: [publicationCatalogMutationKey],
    mutationFn: (input: { channelId: string; publicationId: string }) =>
      createPublicationCatalog(input.channelId, input.publicationId),
    retry: false,
    onMutate: () => [...scope.value] as ChannelScope,
    onSuccess: (_result, _input, captured) =>
      cache.invalidateQueries({ queryKey: channelKeys.root(captured) }),
  });
}
