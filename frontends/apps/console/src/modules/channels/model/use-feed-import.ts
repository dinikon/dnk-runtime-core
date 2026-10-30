import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getFeedImport } from "../api/content-feed.api";
import { useChannelScope } from "./use-channel-scope";
import { contentFeedKeys } from "./content-feed.query-keys";
import type { FeedImport } from "./content-feed.types";
export function useFeedImport(
  channelId: Ref<string>,
  feedId: Ref<string>,
): UseQueryReturnType<FeedImport, Error> {
  const scope = useChannelScope();
  return useQuery({
    queryKey: computed(() =>
      contentFeedKeys.operation(scope.value, channelId.value, feedId.value),
    ),
    queryFn: ({ signal }) =>
      getFeedImport(
        { channelId: channelId.value, feedId: feedId.value },
        signal,
      ),
    enabled: computed(
      () =>
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!channelId.value &&
        !!feedId.value,
    ),
    refetchInterval: (q) =>
      q.state.data &&
      !q.state.data.recoveryRequired &&
      ["queued", "submitting", "processing", "verifying"].includes(
        q.state.data.phase,
      )
        ? 2000
        : false,
    retry: false,
  });
}
