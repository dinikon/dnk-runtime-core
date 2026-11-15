<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import {
  useReceiptExecution,
  useReceiptPosting,
} from "../model/use-receipt-posting-queries";
import ReceiptPostingResult from "../ui/results/ReceiptPostingResult.vue";
const props = defineProps<{ kind: "execution" | "posting" }>(),
  route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope();
const id = computed(() =>
  typeof route.params.identifier === "string" ? route.params.identifier : "",
);
const execution = useReceiptExecution(
    computed(() => (props.kind === "execution" ? id.value : "")),
    scope,
  ),
  posting = useReceiptPosting(
    computed(() => (props.kind === "posting" ? id.value : "")),
    scope,
  );
const query = computed(() =>
    props.kind === "execution" ? execution : posting,
  ),
  result = computed(() => query.value.data.value),
  error = computed(
    () => scope.error.value || query.value.error.value?.message || "",
  ),
  loading = computed(() => query.value.isPending.value);
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
          @click="query.refetch()"
          >Обновить</Button
        >
      </div>
    </header>
    <p v-if="loading" role="status">Загрузка факта…</p>
    <div
      v-if="error"
      role="alert"
      class="shrink-0 rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ error
      }}<Button
        variant="outline"
        :disabled="!scope.ready.value || query.isFetching.value"
        @click="query.refetch()"
        >Повторить</Button
      >
    </div>
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
  </section>
</template>
