import { computed, type Ref } from "vue";
import {
  useQuery,
  useQueryClient,
  type UseQueryReturnType,
} from "@tanstack/vue-query";
import type { ReceiptDocument } from "./receipt.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { receiptKeys } from "./receipt.query-keys";
import { getReceipt } from "../api/receipt.api";
export function useReceiptQuery(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptDocument, Error> {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: computed(() => receiptKeys.detail(scope.key.value, id.value)),
    queryFn: ({ queryKey, signal }) => getReceipt(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 30_000,
    retry: false,
  });
  return {
    ...query,
    refetch: async (options) => {
      const capturedScope = [...scope.key.value] as const;
      const capturedId = id.value;
      const result = await query.refetch(options);
      if (
        !result.error &&
        result.data &&
        scope.ready.value &&
        capturedId === id.value &&
        capturedScope.every((part, index) => part === scope.key.value[index])
      ) {
        // Проверочное чтение могло обнаружить сохранение с потерянным HTTP-ответом.
        await cache.invalidateQueries({
          queryKey: receiptKeys.lists(capturedScope),
        });
      }
      return result;
    },
  };
}
