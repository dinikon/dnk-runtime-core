import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  ReceiptPreparation,
  ReceiptPostingResult,
  ReceiptExecutionHistory,
  ReceiptReferencesParams,
  IntakeReferencesPage,
} from "./receipt-posting.types";
import { receiptPostingKeys } from "./receipt-posting.query-keys";
import {
  prepareReceipt,
  getReceiptExecution,
  getReceiptPosting,
  listReceiptExecutions,
  findReceiptReferences,
} from "../api/receipt-posting.api";
export function useReceiptPreparation(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptPreparation, Error> {
  return useQuery({
    queryKey: computed(() =>
      receiptPostingKeys.context(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => prepareReceipt(queryKey[5], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useReceiptExecution(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptPostingResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      receiptPostingKeys.execution(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => getReceiptExecution(queryKey[5], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
export function useReceiptPosting(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptPostingResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      receiptPostingKeys.posting(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) => getReceiptPosting(queryKey[5], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
export function useReceiptExecutionHistory(
  id: Ref<string>,
  offset: Ref<number>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReceiptExecutionHistory, Error> {
  return useQuery({
    queryKey: computed(() =>
      receiptPostingKeys.history(scope.key.value, id.value, offset.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listReceiptExecutions(queryKey[5], queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
export function useReceiptReferenceQuery(
  id: Ref<string>,
  params: Ref<ReceiptReferencesParams>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): UseQueryReturnType<IntakeReferencesPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      receiptPostingKeys.references(scope.key.value, id.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      findReceiptReferences(queryKey[5], queryKey[6], signal),
    enabled: computed(() => scope.ready.value && enabled.value && !!id.value),
    staleTime: 0,
    retry: false,
  });
}
