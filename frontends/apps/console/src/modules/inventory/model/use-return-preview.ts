import { useQueryClient } from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReturnPreview } from "./return-preview.types";
import type { ReturnExecutionValues } from "./return-posting.types";
import { returnPostingKeys } from "./return-posting.query-keys";
import { previewReturn } from "../api/return-posting.api";
import { returnExecutionSignature } from "./return-execution";
export function returnPreviewSignature(values: ReturnExecutionValues): string {
  return returnExecutionSignature(values);
}
export function useReturnPreview(): {
  calculate: (
    id: string,
    values: ReturnExecutionValues,
    scope: InventoryScope,
    signal: AbortSignal,
  ) => Promise<ReturnPreview>;
} {
  const cache = useQueryClient();
  return {
    calculate: (id, values, scope, signal) =>
      cache.fetchQuery({
        queryKey: returnPostingKeys.preview(
          scope,
          id,
          returnPreviewSignature(values),
        ),
        queryFn: ({ signal: querySignal }) =>
          previewReturn(id, values, AbortSignal.any([signal, querySignal])),
        staleTime: 0,
        retry: false,
      }),
  };
}
