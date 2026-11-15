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
            ? "Исполнение поступления"
            : "Проводка поступления"
        }}
      </h1>
      <div class="flex gap-2">
        <Button
          variant="outline"
          @click="router.push({ name: 'inventory-receipt-documents' })"
          >К поступлениям</Button
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
