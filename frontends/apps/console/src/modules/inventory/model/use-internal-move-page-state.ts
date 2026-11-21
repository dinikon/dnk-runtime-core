import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  parseInternalMovePage,
  internalMovePageQuery,
} from "./internal-move-page-state";
import type { InternalMovesParams } from "./internal-move.types";
export interface InternalMovePageState {
  params: ComputedRef<InternalMovesParams>;
  change(v: Partial<InternalMovesParams>): void;
  page(offset: number): void;
}
export function useInternalMovePageState(): InternalMovePageState {
  const route = useRoute(),
    router = useRouter(),
    params = computed(() => parseInternalMovePage(route.query));
  const replace = (v: InternalMovesParams): void => {
    void router.replace({ query: internalMovePageQuery(v) });
  };
  return {
    params,
    change: (v) => replace({ ...params.value, ...v, offset: 0 }),
    page: (offset) => replace({ ...params.value, offset }),
  };
}
