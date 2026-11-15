import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parseWriteOffPage, writeOffPageQuery } from "./write-off-page-state";
import type { WriteOffsParams } from "./write-off.types";
export interface WriteOffPageState {
  params: ComputedRef<WriteOffsParams>;
  change(v: Partial<WriteOffsParams>): void;
  page(offset: number): void;
}
export function useWriteOffPageState(): WriteOffPageState {
  const route = useRoute(),
    router = useRouter(),
    params = computed(() => parseWriteOffPage(route.query));
  const replace = (v: WriteOffsParams): void => {
    void router.replace({ query: writeOffPageQuery(v) });
  };
  return {
    params,
    change: (v) => replace({ ...params.value, ...v, offset: 0 }),
    page: (offset) => replace({ ...params.value, offset }),
  };
}
