import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { resumeFeedImport } from "../api/content-feed.api";
import { useChannelScope } from "./use-channel-scope";
import { contentFeedKeys } from "./content-feed.query-keys";
import type { ChannelScope } from "./channel.query-keys";
import type { FeedImportRevisionInput, FeedImport } from "./content-feed.types";

export function useResumeFeedImport(): UseMutationReturnType<
  FeedImport,
  Error,
  FeedImportRevisionInput,
  ChannelScope
> {
  const scope = useChannelScope(),
    cache = useQueryClient();
  return useMutation({
    mutationKey: computed(() =>
      contentFeedKeys.mutation(scope.value, "resumeFeedImport"),
    ),
    mutationFn: resumeFeedImport,
    retry: false,
    onMutate: async (input) => {
      const captured = [...scope.value] as ChannelScope;
      await cache.cancelQueries({
        queryKey: contentFeedKeys.list(captured, input.channelId),
      });
      if (JSON.stringify(captured) !== JSON.stringify(scope.value))
        throw new Error("Рабочее пространство изменилось. Обновите страницу.");
      return captured;
    },
    onSuccess: (result, input, previous) => {
      if (!previous || JSON.stringify(previous) !== JSON.stringify(scope.value))
        return;
      cache.setQueryData(
        contentFeedKeys.operation(previous, input.channelId, input.feedId),
        result,
      );
      void cache.invalidateQueries({
        queryKey: contentFeedKeys.list(previous, input.channelId),
      });
    },
    onError: (_error, input, previous) => {
      if (!previous || JSON.stringify(previous) !== JSON.stringify(scope.value))
        return;
      void cache.invalidateQueries({
        queryKey: contentFeedKeys.list(previous, input.channelId),
      });
    },
  });
}
