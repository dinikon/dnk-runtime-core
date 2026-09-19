<script setup lang="ts">
import { ref } from "vue";
import { FileSpreadsheet, Plus, RefreshCw } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useDeletePriceList } from "../model/use-delete-price-list";
import { usePriceListAction, type PriceListAction } from "../model/use-price-list-action";
import { usePriceListsQuery } from "../model/use-price-lists-query";
import type { PriceList, PriceListScope } from "../model/types";
import DeletePriceListConfirmDialog from "../ui/management/DeletePriceListConfirmDialog.vue";
import PriceListsTable from "../ui/management/PriceListsTable.vue";

const scope = ref<PriceListScope>("current");
const selectedDelete = ref<PriceList | null>(null);
const priceLists = usePriceListsQuery(scope);
const action = usePriceListAction();
const deleteMutation = useDeletePriceList();

function runAction(item: PriceList, nextAction: PriceListAction) {
  action.mutate({ id: item.id, action: nextAction });
}
async function confirmDelete(confirmationTitle: string) {
  if (!selectedDelete.value) return;
  await deleteMutation.mutateAsync({ id: selectedDelete.value.id, confirmationTitle });
  selectedDelete.value = null;
}
</script>

<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div><p class="text-sm text-muted-foreground">Закупки</p><h1 class="text-2xl font-semibold tracking-tight">Прайс-листы</h1><p class="mt-1 text-sm text-muted-foreground">Источники закупочных цен, РРЦ и остатков партнёров.</p></div>
      <Button as-child><RouterLink to="/purchases/price-lists/new"><Plus data-icon="inline-start" />Новый прайс-лист</RouterLink></Button>
    </header>
    <ToggleGroup :model-value="scope" type="single" variant="outline" aria-label="Фильтр прайс-листов" @update:model-value="(value) => { if (value) scope = value as PriceListScope }">
      <ToggleGroupItem value="current">Текущие</ToggleGroupItem><ToggleGroupItem value="archived">Архивные</ToggleGroupItem><ToggleGroupItem value="all">Все</ToggleGroupItem>
    </ToggleGroup>
    <div v-if="priceLists.isPending.value" class="grid gap-3" role="status"><Skeleton v-for="item in 4" :key="item" class="h-16" /></div>
    <Card v-else-if="priceLists.isError.value"><CardContent class="flex items-center justify-between py-6"><p>Не удалось загрузить прайс-листы.</p><Button variant="outline" @click="priceLists.refetch()"><RefreshCw data-icon="inline-start" />Повторить</Button></CardContent></Card>
    <Card v-else-if="!priceLists.data.value?.length"><CardContent class="flex min-h-64 flex-col items-center justify-center gap-3 text-center"><div class="rounded-full bg-muted p-3"><FileSpreadsheet /></div><div><p class="font-medium">{{ scope === 'archived' ? 'Архив пуст' : 'Прайс-листов пока нет' }}</p><p class="text-sm text-muted-foreground">{{ scope === 'archived' ? 'Архивированные прайс-листы появятся здесь.' : 'Добавьте XML, YAML или XLSX источник партнёра.' }}</p></div><Button v-if="scope !== 'archived'" as-child><RouterLink to="/purchases/price-lists/new">Создать прайс-лист</RouterLink></Button></CardContent></Card>
    <PriceListsTable v-else :items="priceLists.data.value ?? []" @action="runAction" @delete="selectedDelete = $event" />
    <DeletePriceListConfirmDialog :open="selectedDelete !== null" :price-list="selectedDelete" :pending="deleteMutation.isPending.value" @update:open="(open) => { if (!open) selectedDelete = null }" @confirm="confirmDelete" />
  </div>
</template>
