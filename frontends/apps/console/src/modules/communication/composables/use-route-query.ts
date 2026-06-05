import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

type QueryPatch = Record<string, string | undefined>;

export function useRouteQueryPatch() {
  const route = useRoute();
  const router = useRouter();

  function patchQuery(patch: QueryPatch) {
    const nextQuery = { ...route.query };

    for (const [key, value] of Object.entries(patch)) {
      if (!value) {
        delete nextQuery[key];
      } else {
        nextQuery[key] = value;
      }
    }

    router.replace({ query: nextQuery });
  }

  return { patchQuery, route };
}

export function useRouteSearchQuery() {
  const { route } = useRouteQueryPatch();

  return computed(() => {
    const value = route.query.q;
    return typeof value === "string" ? value : "";
  });
}

export function useRouteQueryFlag(key: string, value: string) {
  const { patchQuery, route } = useRouteQueryPatch();

  return computed({
    get: () => route.query[key] === value,
    set: (isOpen: boolean) => {
      patchQuery({ [key]: isOpen ? value : undefined });
    },
  });
}
