import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  publicationDetailsTab,
  type PublicationDetailsTab,
} from "./publication-navigation";

export function usePublicationDetailsPageState(): {
  tab: ComputedRef<PublicationDetailsTab>;
  selectTab(value: string | number): void;
} {
  const route = useRoute(),
    router = useRouter();
  return {
    tab: computed(() => publicationDetailsTab(route.query)),
    selectTab(value): void {
      if (value !== "positions" && value !== "bindings") return;
      void router.replace({
        query: {
          ...route.query,
          publication_tab: value === "positions" ? undefined : value,
        },
        hash: route.hash,
      });
    },
  };
}
