import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { feedApi } from "../api/feed.api";
import { feedKeys } from "./feed.query-keys";
import { useFeedScope } from "./use-feed-scope";
import type { Feed, FeedPage, FeedFilters } from "./feed.types";
export function useFeeds(
  filters: Ref<FeedFilters>,
): UseQueryReturnType<FeedPage, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => feedKeys.list(scope.value, filters.value)),
    queryFn: ({ signal }) => feedApi.list({ ...filters.value }, signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1]),
    retry: false,
  });
}
export function useFeed(id: Ref<string>): UseQueryReturnType<Feed, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => feedKeys.detail(scope.value, id.value)),
    queryFn: ({ signal }) => feedApi.get(id.value, signal),
    enabled: computed(() => !!id.value && !!scope.value[0] && !!scope.value[1]),
    retry: false,
  });
}
