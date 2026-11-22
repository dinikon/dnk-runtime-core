import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { feedPreviewApi } from "../api/feed-preview.api";
import { feedPreviewKeys } from "./feed-preview.query-keys";
import type { FeedPreview } from "./feed-preview.types";
import { useFeedScope } from "./use-feed-scope";

export function useFeedPreview(
  id: Ref<string>,
  version: Ref<number | null>,
): UseQueryReturnType<FeedPreview, Error> {
  const scope = useFeedScope();
  const key = computed(() =>
    feedPreviewKeys.sample(scope.value, id.value, version.value),
  );
  return useQuery({
    queryKey: key,
    queryFn: ({ queryKey, signal }) => {
      const expectedVersion = queryKey[6];
      if (expectedVersion === null) throw new Error("Версия фида недоступна.");
      return feedPreviewApi.preview(
        { feedId: queryKey[5], expectedVersion },
        signal,
      );
    },
    enabled: computed(
      () =>
        !!scope.value[0] &&
        !!scope.value[1] &&
        !!id.value &&
        version.value !== null,
    ),
    placeholderData: (previous, query) => {
      const identity = key.value.slice(0, -1);
      if (identity.every((value, index) => value === query?.queryKey[index]))
        return previous;
      return undefined;
    },
    retry: false,
  });
}
