import { computed } from "vue";
import type { WritableComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { headerExampleTabs } from "./header-example.constants";

interface HeaderExamplePageState {
  activeTab: WritableComputedRef<string>;
  search: WritableComputedRef<string>;
}

export function useHeaderExamplePageState(): HeaderExamplePageState {
  const route = useRoute();
  const router = useRouter();

  const activeTab = computed({
    get: (): string =>
      headerExampleTabs.some((tab) => tab.value === route.query.tab)
        ? String(route.query.tab)
        : "profile",
    set: (value: string): void => {
      void router.replace({
        query: { ...route.query, tab: value === "profile" ? undefined : value },
      });
    },
  });
  const search = computed({
    get: (): string =>
      typeof route.query.search === "string" ? route.query.search : "",
    set: (value: string): void => {
      void router.replace({
        query: { ...route.query, search: value || undefined },
      });
    },
  });

  return { activeTab, search };
}
