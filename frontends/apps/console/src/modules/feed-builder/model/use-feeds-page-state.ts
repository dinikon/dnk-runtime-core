import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { feedFilters } from "./feed.navigation";
import type { FeedFilters } from "./feed.types";
export function useFeedsPageState(): {
  filters: import("vue").ComputedRef<FeedFilters>;
  setFilter(key: "search" | "status", value: string): void;
  setOffset(offset: number): void;
  reset(): void;
} {
  const route = useRoute(),
    router = useRouter();
  const filters = computed(() => feedFilters(route.query));
  function replace(values: Record<string, string | undefined>): void {
    void router.replace({
      query: { ...route.query, ...values },
      hash: route.hash,
    });
  }
  return {
    filters,
    setFilter: (key, value) =>
      replace({
        [key === "search" ? "q" : "status"]: value || undefined,
        offset: undefined,
      }),
    setOffset: (offset) =>
      replace({ offset: offset > 0 ? String(offset) : undefined }),
    reset: () =>
      replace({ q: undefined, status: undefined, offset: undefined }),
  };
}
