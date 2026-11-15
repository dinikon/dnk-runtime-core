<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { StockAccountingRequestError } from "../api/stock-accounting.api";
import { useInventoryScope } from "../model/use-inventory-scope";
import {
  useReceiptExecution,
  useReceiptPosting,
} from "../model/use-receipt-posting-queries";
import {
  useGetStockExecutionDetails,
  useGetStockPostingDetails,
} from "../model/use-stock-accounting-queries";
import {
  accountingTarget,
  stockReadLocation,
  type StockAccountingTarget,
} from "../model/stock-accounting-navigation";
import { useInternalMoveQuery } from "../model/use-internal-move-query";
import { useInternalMoveExecutionResult } from "../model/use-internal-move-execution-result";
import InternalMoveExecutionResult from "../ui/results/InternalMoveExecutionResult.vue";
import { useIssueQuery } from "../model/use-issue-query";
import { useReceiptQuery } from "../model/use-receipt-query";
import { useIssueExecutionResult } from "../model/use-issue-execution-result";
import IssueExecutionResult from "../ui/results/IssueExecutionResult.vue";
import StockFactDetails from "../ui/results/StockFactDetails.vue";
import ReceiptPostingResult from "../ui/results/ReceiptPostingResult.vue";
const props = defineProps<{ kind: "execution" | "posting" }>(),
  route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  typeof route.params.identifier === "string" ? route.params.identifier : "",
);
const canonicalExecution = useGetStockExecutionDetails(
  id,
  scope,
  computed(() => props.kind === "execution"),
);
const canonicalPosting = useGetStockPostingDetails(
  id,
  scope,
  computed(() => props.kind === "posting"),
);
const canonical = computed(() =>
  props.kind === "execution" ? canonicalExecution : canonicalPosting,
);
const fact = computed(() =>
  scope.ready.value &&
  !(
    canonical.value.error.value instanceof StockAccountingRequestError &&
    [403, 404].includes(canonical.value.error.value.status ?? 0)
  )
    ? canonical.value.data.value
    : undefined,
);
const execution = useReceiptExecution(
    computed(() =>
      props.kind === "execution" && fact.value?.hasReceiptResult
        ? id.value
        : "",
    ),
    scope,
  ),
  posting = useReceiptPosting(
    computed(() =>
      props.kind === "posting" && fact.value?.hasReceiptResult ? id.value : "",
    ),
    scope,
  );
const query = computed(() =>
    props.kind === "execution" ? execution : posting,
  ),
  result = computed(() =>
    query.value.error.value instanceof StockAccountingRequestError &&
    [403, 404].includes(query.value.error.value.status ?? 0)
      ? undefined
      : query.value.data.value,
  ),
  error = computed(
    () => scope.error.value || query.value.error.value?.message || "",
  ),
  loading = computed(
    () => query.value.isPending.value && !!fact.value?.hasReceiptResult,
  );
const issueResult = useIssueExecutionResult(
  computed(() =>
    fact.value?.operationType === "ISSUE" ? fact.value.executionId : "",
  ),
  scope,
);
const receiptDocument = useReceiptQuery(
  computed(() =>
    fact.value?.operationType === "RECEIPT" ? fact.value.documentId : "",
  ),
  scope,
);
const issueDocument = useIssueQuery(
  computed(() =>
    fact.value?.operationType === "ISSUE" ? fact.value.documentId : "",
  ),
  scope,
);
const internalMoveDocument = useInternalMoveQuery(
  computed(() =>
    fact.value?.operationType === "INTERNAL_MOVE" ? fact.value.documentId : "",
  ),
  scope,
);
const internalMoveResult = useInternalMoveExecutionResult(
  computed(() =>
    fact.value?.operationType === "INTERNAL_MOVE" ? fact.value.executionId : "",
  ),
  scope,
);
const currentDocument = computed(() =>
  fact.value?.operationType === "INTERNAL_MOVE"
    ? internalMoveDocument
    : fact.value?.operationType === "ISSUE"
      ? issueDocument
      : receiptDocument,
);
const canReceiveMore = computed(() => {
  const document = currentDocument.value.data.value;
  return (
    scope.ready.value &&
    !currentDocument.value.error.value &&
    !!document &&
    document.id === fact.value?.documentId &&
    document.sourceSystem === null &&
    ["CONFIRMED", "PARTIALLY_EXECUTED"].includes(document.status)
  );
});
function navigateAccounting(target: StockAccountingTarget): void {
  void router.push(accountingTarget(target));
}
function openMovements(): void {
  if (fact.value)
    void router.push(
      stockReadLocation("movements", { executionId: fact.value.executionId }),
    );
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    :aria-label="
      kind === 'execution' ? 'Карточка исполнения' : 'Карточка проводки'
    "
  >
    <header class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <h1 class="text-2xl font-semibold">
        {{
          kind === "execution"
            ? fact?.operationType === "INTERNAL_MOVE"
              ? "Исполнение перемещения"
              : fact?.operationType === "ISSUE"
                ? "Исполнение расхода"
                : "Исполнение поступления"
            : fact?.operationType === "INTERNAL_MOVE"
              ? "Проводка перемещения"
              : fact?.operationType === "ISSUE"
                ? "Проводка расхода"
                : "Проводка поступления"
        }}
      </h1>
      <div class="flex flex-wrap gap-2">
        <Button
          v-if="canReceiveMore && fact"
          :disabled="currentDocument.isFetching.value"
          @click="
            router.push({
              name:
                fact.operationType === 'INTERNAL_MOVE'
                  ? 'inventory-internal-move-execute'
                  : fact.operationType === 'ISSUE'
                    ? 'inventory-issue-execute'
                    : 'inventory-receipt-receive',
              params: { documentId: fact.documentId },
            })
          "
          >{{
            fact.operationType === "INTERNAL_MOVE"
              ? "Переместить остаток"
              : fact.operationType === "ISSUE"
                ? "Выдать остаток"
                : "Принять остаток"
          }}</Button
        >
        <Button
          variant="outline"
          @click="
            router.push({
              name:
                fact?.operationType === 'INTERNAL_MOVE'
                  ? 'inventory-internal-move-documents'
                  : fact?.operationType === 'ISSUE'
                    ? 'inventory-issue-documents'
                    : 'inventory-receipt-documents',
            })
          "
          >{{
            fact?.operationType === "INTERNAL_MOVE"
              ? "К перемещениям"
              : fact?.operationType === "ISSUE"
                ? "К расходам"
                : "К поступлениям"
          }}</Button
        ><Button
          variant="outline"
          :disabled="!scope.ready.value || query.isFetching.value"
          @click="
            query.refetch();
            canonical.refetch();
          "
          >Обновить</Button
        >
      </div>
    </header>
    <p v-if="loading" role="status">Загрузка факта…</p>
    <div
      v-if="error && !fact"
      role="alert"
      class="shrink-0 rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ error
      }}<Button
        variant="outline"
        :disabled="!scope.ready.value || query.isFetching.value"
        @click="
          query.refetch();
          canonical.refetch();
        "
        >Повторить</Button
      >
    </div>
    <p v-if="canonical.isPending.value" role="status">
      Загрузка учётного основания…
    </p>
    <p v-if="canonical.error.value" role="alert" class="text-destructive">
      {{ canonical.error.value.message
      }}<Button variant="outline" @click="canonical.refetch()"
        >Повторить чтение факта</Button
      >
    </p>
    <StockFactDetails
      v-if="fact && scope.ready.value"
      :fact="fact"
      @navigate="navigateAccounting"
      @movements="openMovements"
    />
    <InternalMoveExecutionResult
      v-if="
        fact?.operationType === 'INTERNAL_MOVE' &&
        internalMoveResult.data.value &&
        scope.ready.value
      "
      :result="internalMoveResult.data.value"
    />
    <p
      v-if="
        fact?.operationType === 'INTERNAL_MOVE' &&
        internalMoveResult.isPending.value
      "
      role="status"
    >
      Загрузка исходного результата перемещения…
    </p>
    <p
      v-if="
        fact?.operationType === 'INTERNAL_MOVE' &&
        internalMoveResult.error.value
      "
      role="alert"
      class="text-sm text-destructive"
    >
      {{ internalMoveResult.error.value.message
      }}<Button variant="outline" @click="internalMoveResult.refetch()"
        >Повторить чтение исходного результата</Button
      >
    </p>
    <IssueExecutionResult
      v-if="
        fact?.operationType === 'ISSUE' &&
        issueResult.data.value &&
        scope.ready.value
      "
      :result="issueResult.data.value"
    />
    <p
      v-if="fact?.operationType === 'ISSUE' && issueResult.error.value"
      role="alert"
      class="text-sm text-destructive"
    >
      {{ issueResult.error.value.message
      }}<Button variant="outline" @click="issueResult.refetch()"
        >Повторить чтение исходного результата</Button
      >
    </p>
    <details
      v-if="fact?.hasReceiptResult && result && scope.ready.value"
      class="shrink-0 rounded-lg border p-4"
    >
      <summary class="cursor-pointer text-sm font-medium">
        Первоначальный результат приёмки
      </summary>
      <ReceiptPostingResult
        v-if="result && scope.ready.value"
        :result="result"
        @document="
          router.push({
            name: 'inventory-receipt-document',
            params: { documentId: result.documentId },
          })
        "
        @execution="
          router.push({
            name: 'inventory-stock-execution',
            params: { identifier: result.executionId },
          })
        "
        @posting="
          router.push({
            name: 'inventory-stock-posting',
            params: { identifier: result.postingId },
          })
        "
      />
    </details>
  </section>
</template>
