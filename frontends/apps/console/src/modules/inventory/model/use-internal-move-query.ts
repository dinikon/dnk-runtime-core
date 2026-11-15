import { computed, type Ref } from "vue";
import {
  useQuery,
  useQueryClient,
  type UseQueryReturnType,
} from "@tanstack/vue-query";
import type { InternalMoveDocument } from "./internal-move.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { internalMoveKeys } from "./internal-move.query-keys";
import { getInternalMove } from "../api/internal-move.api";
export function useInternalMoveQuery(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMoveDocument, Error> {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: computed(() =>
      internalMoveKeys.detail(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => getInternalMove(queryKey[6], signal),
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
          queryKey: internalMoveKeys.lists(capturedScope),
        });
      }
      return result;
    },
  };
}
