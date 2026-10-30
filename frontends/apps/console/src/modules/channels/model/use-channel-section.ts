import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";

export function useChannelSection(
  hasFeed: ComputedRef<boolean>,
): ComputedRef<string> {
  const route = useRoute();
  const router = useRouter();
  return computed({
    get: () =>
      hasFeed.value && route.query.section === "content-feed"
        ? "content-feed"
        : "publications",
    set: (section: string) => {
      void router.replace({
        query: {
          ...route.query,
          section: section === "content-feed" ? section : undefined,
        },
      });
    },
  });
}
