import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parseReceiptPage, receiptPageQuery } from "./receipt-page-state";
import type { ReceiptsParams } from "./receipt.types";
export interface ReceiptPageState {
  params: ComputedRef<ReceiptsParams>;
  change(v: Partial<ReceiptsParams>): void;
  page(offset: number): void;
}
export function useReceiptPageState(): ReceiptPageState {
  const route = useRoute(),
    router = useRouter(),
    params = computed(() => parseReceiptPage(route.query));
  const replace = (v: ReceiptsParams): void => {
    void router.replace({ query: receiptPageQuery(v) });
  };
  return {
    params,
    change: (v) => replace({ ...params.value, ...v, offset: 0 }),
    page: (offset) => replace({ ...params.value, offset }),
  };
}
