import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { ReceiptsPage, ReceiptsParams } from "./receipt.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { receiptKeys } from "./receipt.query-keys";
import { listReceipts } from "../api/receipt.api";
export function useReceiptsQuery(
  params: Ref<ReceiptsParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptsPage, Error> {
  return useQuery({
    queryKey: computed(() => receiptKeys.list(scope.key.value, params.value)),
    queryFn: ({ queryKey, signal }) => listReceipts(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
