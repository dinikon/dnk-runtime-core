import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parseCompaniesExampleParams } from "./companies-example.selectors.ts";
import type { CompaniesExampleParams } from "./companies-example.types";

interface CompaniesExamplePageState {
  params: ComputedRef<CompaniesExampleParams>;
  update: (patch: Partial<CompaniesExampleParams>) => void;
  reset: () => void;
}

export function useCompaniesExamplePageState(): CompaniesExamplePageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => parseCompaniesExampleParams(route.query));
  function update(patch: Partial<CompaniesExampleParams>): void {
    const next = { ...params.value, ...patch };
    void router.replace({
      query: {
        ...route.query,
        search: next.search || undefined,
        icp: next.icp === "all" ? undefined : next.icp,
        sort: next.sort === "original" ? undefined : next.sort,
      },
      hash: route.hash,
    });
  }
  return {
    params,
    update,
    reset: () => update({ search: "", icp: "all", sort: "original" }),
  };
}
