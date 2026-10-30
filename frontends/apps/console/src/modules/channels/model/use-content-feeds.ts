import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getContentFeeds } from "../api/content-feed.api";
import { useChannelScope } from "./use-channel-scope";
import { contentFeedKeys } from "./content-feed.query-keys";
import type { ContentFeed } from "./content-feed.types";
export function useContentFeeds(
  channelId: Ref<string>,
): UseQueryReturnType<ContentFeed[], Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      contentFeedKeys.list(scope.value, channelId.value),
    ),
    queryFn: ({ signal }) => getContentFeeds(channelId.value, signal),
    enabled: computed(
      () => !!scope.value[0] && !!scope.value[1] && !!channelId.value,
    ),
    retry: false,
  });
}
