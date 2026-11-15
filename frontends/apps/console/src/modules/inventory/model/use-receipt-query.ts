import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { ReceiptDocument } from "./receipt.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { receiptKeys } from "./receipt.query-keys";
import { getReceipt } from "../api/receipt.api";
export function useReceiptQuery(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptDocument, Error> {
  return useQuery({
    queryKey: computed(() => receiptKeys.detail(scope.key.value, id.value)),
    queryFn: ({ queryKey, signal }) => getReceipt(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 30_000,
    retry: false,
  });
}
