import { computed } from "vue";
import {
  useQuery,
  useQueryClient,
  type UseQueryReturnType,
} from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type {
  StatusTransition,
  StatusChangePreview,
} from "./status-change-preview.types";
import type { StatusChangeExecutionValues } from "./status-change-posting.types";
import { statusChangePostingKeys } from "./status-change-posting.query-keys";
import {
  previewStatusChange,
  getStatusTransitions,
} from "../api/status-change-posting.api";
import { statusChangeExecutionSignature } from "./status-change-execution";
export function useStatusTransitions(
  scope: InventoryScopeState,
): UseQueryReturnType<StatusTransition[], Error> {
  return useQuery({
    queryKey: computed(() =>
      statusChangePostingKeys.transitions(scope.key.value),
    ),
    queryFn: ({ signal }) => getStatusTransitions(signal),
    enabled: computed(() => scope.ready.value),
    retry: false,
  });
}
export function statusChangePreviewSignature(
  values: StatusChangeExecutionValues,
): string {
  return statusChangeExecutionSignature(values);
}
export function useStatusChangePreview(): {
  calculate: (
    id: string,
    values: StatusChangeExecutionValues,
    scope: InventoryScope,
    signal: AbortSignal,
  ) => Promise<StatusChangePreview>;
} {
  const cache = useQueryClient();
  return {
    calculate: (id, values, scope, signal) =>
      cache.fetchQuery({
        queryKey: statusChangePostingKeys.preview(
          scope,
          id,
          statusChangePreviewSignature(values),
        ),
        queryFn: ({ signal: querySignal }) =>
          previewStatusChange(
            id,
            values,
            AbortSignal.any([signal, querySignal]),
          ),
        staleTime: 0,
        retry: false,
      }),
  };
}
