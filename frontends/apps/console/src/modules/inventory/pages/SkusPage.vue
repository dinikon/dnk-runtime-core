<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { useSkus } from "../model/queries";
import { inventoryError } from "../model/forms";
import RequestError from "../ui/RequestError.vue";
import SkusTable from "../ui/SkusTable.vue";
const skus = useSkus();
const items = computed(() => [
  ...new Map(
    (skus.data.value?.pages.flat() ?? []).map((item) => [item.id, item]),
  ).values(),
]);
function retry() {
  if (skus.isFetchNextPageError.value) void skus.fetchNextPage();
  else void skus.refetch();
}
</script>
<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <h1 class="text-2xl font-semibold">SKU</h1>
      <Button as-child
        ><RouterLink to="/inventory/skus/new">Создать SKU</RouterLink></Button
      >
    </header>
    <Skeleton
      v-if="skus.isPending.value"
      class="h-48"
      aria-label="Загрузка SKU"
    /><RequestError
      v-if="skus.isError.value"
      :message="inventoryError(skus.error.value)"
      retry
      :pending="skus.isFetching.value"
      @retry="retry"
    /><Card
      v-if="!skus.isPending.value && (items.length || !skus.isError.value)"
      ><CardHeader
        ><CardTitle>Учётные единицы</CardTitle
        ><CardDescription>{{
          items.length
            ? "Откройте SKU для просмотра данных и создания товара."
            : "SKU пока нет. Создайте первую учётную единицу."
        }}</CardDescription></CardHeader
      ><CardContent
        ><SkusTable v-if="items.length" :items="items" /></CardContent></Card
    ><Button
      v-if="skus.hasNextPage.value"
      variant="outline"
      class="self-start"
      :disabled="skus.isFetching.value"
      @click="skus.fetchNextPage()"
      >{{
        skus.isFetchingNextPage.value ? "Загрузка…" : "Загрузить ещё"
      }}</Button
    >
  </div>
</template>
