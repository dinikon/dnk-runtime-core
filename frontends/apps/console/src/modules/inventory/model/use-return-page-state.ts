import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parseReturnPage, returnPageQuery } from "./return-page-state";
import type { ReturnsParams } from "./return.types";
export interface ReturnPageState {
  params: ComputedRef<ReturnsParams>;
  change(v: Partial<ReturnsParams>): void;
  page(offset: number): void;
}
export function useReturnPageState(): ReturnPageState {
  const route = useRoute(),
    router = useRouter(),
    params = computed(() => parseReturnPage(route.query));
  const replace = (v: ReturnsParams): void => {
    void router.replace({ query: returnPageQuery(v) });
  };
  return {
    params,
    change: (v) => replace({ ...params.value, ...v, offset: 0 }),
    page: (offset) => replace({ ...params.value, offset }),
  };
}
