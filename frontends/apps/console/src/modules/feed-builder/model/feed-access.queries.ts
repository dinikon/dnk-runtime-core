import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { feedAccessApi } from "../api/feed-access.api";
import { feedKeys, type FeedScope } from "./feed.query-keys";
import { useFeedScope } from "./use-feed-scope";
import type { FeedAccessToken } from "./feed-access.types";

export const feedAccessKeys = {
  tokens: (scope: FeedScope, id: string) => [...feedKeys.root(scope), "access-tokens", id] as const,
};

export function useFeedAccessTokens(
  feedId: Ref<string>, canManage: Ref<boolean>,
): UseQueryReturnType<FeedAccessToken[], Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => feedAccessKeys.tokens(scope.value, feedId.value)),
    queryFn: ({ queryKey, signal }) => feedAccessApi.list(queryKey[5], signal),
    enabled: computed(() => !!(canManage.value && scope.value[0] && scope.value[1] && feedId.value)),
    retry: false,
  });
}
