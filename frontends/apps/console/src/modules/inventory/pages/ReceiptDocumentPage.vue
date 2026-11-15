<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useReceiptQuery } from "../model/use-receipt-query";
import ReceiptDocumentDetails from "../ui/results/ReceiptDocumentDetails.vue";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope(),
  id = computed(() =>
    typeof route.params.documentId === "string" ? route.params.documentId : "",
  ),
  query = useReceiptQuery(id, scope),
  notice = ref("");
watch(
  () => [...scope.key.value, id.value],
  () => (notice.value = ""),
);
function back(): void {
  const path = route.query.returnTo;
  void router.push(
    typeof path === "string" &&
      /^\/inventory\/stock-documents(?:\?|$)/.test(path)
      ? path
      : { name: "inventory-receipt-documents" },
  );
}
async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(id.value);
    notice.value = "Идентификатор скопирован.";
  } catch {
    notice.value =
      "Не удалось скопировать. Идентификатор можно выделить вручную.";
  }
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка поступления"
  >
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <h1 class="text-2xl font-semibold">Поступление</h1>
        <p class="mt-1 break-all font-mono text-xs text-muted-foreground">
          {{ id }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button variant="outline" @click="back">К списку</Button
        ><Button
          variant="outline"
          :disabled="!query.data.value || !scope.ready.value"
          @click="copy"
          >Копировать ID</Button
        ><Button
          variant="outline"
          :disabled="!scope.ready.value || query.isFetching.value"
          @click="query.refetch()"
          >Обновить</Button
        >
      </div>
    </header>
    <p v-if="notice" role="status" class="text-sm text-muted-foreground">
      {{ notice }}
    </p>
    <div
      v-if="scope.error.value || query.error.value"
      role="alert"
      class="rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ scope.error.value || query.error.value?.message }}
      <Button
        variant="outline"
        :disabled="!scope.ready.value || query.isFetching.value"
        @click="query.refetch()"
        >Повторить</Button
      >
    </div>
    <p v-if="query.isPending.value" role="status">Загрузка поступления…</p>
    <p
      v-else-if="query.isFetching.value"
      role="status"
      class="text-xs text-muted-foreground"
    >
      Обновление…
    </p>
    <ReceiptDocumentDetails
      v-if="query.data.value && scope.ready.value"
      :document="query.data.value"
    />
  </section>
</template>
