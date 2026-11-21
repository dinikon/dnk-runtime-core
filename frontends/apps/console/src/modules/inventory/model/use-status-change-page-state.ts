import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  parseStatusChangePage,
  statusChangePageQuery,
} from "./status-change-page-state";
import type { StatusChangesParams } from "./status-change.types";
export interface StatusChangePageState {
  params: ComputedRef<StatusChangesParams>;
  change(v: Partial<StatusChangesParams>): void;
  page(offset: number): void;
}
export function useStatusChangePageState(): StatusChangePageState {
  const route = useRoute(),
    router = useRouter(),
    params = computed(() => parseStatusChangePage(route.query));
  const replace = (v: StatusChangesParams): void => {
    void router.replace({ query: statusChangePageQuery(v) });
  };
  return {
    params,
    change: (v) => replace({ ...params.value, ...v, offset: 0 }),
    page: (offset) => replace({ ...params.value, offset }),
  };
}
