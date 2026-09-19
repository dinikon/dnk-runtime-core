<script setup lang="ts">
import { FileSpreadsheet, MoreHorizontal, Plus, RefreshCw } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePriceListAction } from "../model/use-price-list-action";
import { usePriceListsQuery } from "../model/use-price-lists-query";

const priceLists = usePriceListsQuery();
const action = usePriceListAction();

const statusLabel: Record<string, string> = {
  draft: "Черновик",
  ready: "Готов",
  active: "Активен",
  paused: "На паузе",
  invalid: "Ошибка",
};
</script>

<template>
  <div class="flex min-h-0 flex-col gap-5 overflow-y-auto pb-6">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm text-muted-foreground">Закупки</p>
        <h1 class="text-2xl font-semibold tracking-tight">Прайс-листы</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Источники закупочных цен, РРЦ и остатков партнёров.
        </p>
      </div>
      <Button as-child><RouterLink to="/purchases/price-lists/new"><Plus />Новый прайс-лист</RouterLink></Button>
    </header>

    <div v-if="priceLists.isPending.value" class="grid gap-3" role="status">
      <div v-for="item in 4" :key="item" class="h-16 animate-pulse rounded-lg bg-muted" />
    </div>
    <Card v-else-if="priceLists.isError.value">
      <CardContent class="flex items-center justify-between py-6">
        <p>Не удалось загрузить прайс-листы.</p>
        <Button variant="outline" @click="priceLists.refetch()"><RefreshCw />Повторить</Button>
      </CardContent>
    </Card>
    <Card v-else-if="!priceLists.data.value?.length">
      <CardContent class="flex min-h-64 flex-col items-center justify-center gap-3 text-center">
        <div class="rounded-full bg-muted p-3"><FileSpreadsheet class="size-6" /></div>
        <div><p class="font-medium">Прайс-листов пока нет</p><p class="text-sm text-muted-foreground">Добавьте XML, YAML или XLSX источник партнёра.</p></div>
        <Button as-child><RouterLink to="/purchases/price-lists/new">Создать прайс-лист</RouterLink></Button>
      </CardContent>
    </Card>
    <div v-else class="overflow-hidden rounded-lg border bg-background">
      <Table>
        <TableHeader><TableRow>
          <TableHead>Название</TableHead><TableHead>Источник</TableHead><TableHead>Статус</TableHead><TableHead>Офферы</TableHead>
          <TableHead>Следующая загрузка</TableHead><TableHead>Последняя загрузка</TableHead><TableHead><span class="sr-only">Действия</span></TableHead>
        </TableRow></TableHeader>
        <TableBody>
          <TableRow v-for="item in priceLists.data.value" :key="item.id">
            <TableCell><RouterLink class="font-medium hover:underline" :to="`/purchases/price-lists/${item.id}`">{{ item.title }}</RouterLink></TableCell>
            <TableCell><div class="uppercase">{{ item.source_format }}</div><div class="max-w-72 truncate text-xs text-muted-foreground">{{ item.source_url_display }}</div></TableCell>
            <TableCell><Badge :variant="item.status === 'active' ? 'secondary' : 'outline'">{{ statusLabel[item.status] }}</Badge></TableCell>
            <TableCell>{{ item.active_offer_count ?? 0 }}</TableCell>
            <TableCell>{{ item.next_sync_at ? new Date(item.next_sync_at).toLocaleString("uk-UA") : "—" }}</TableCell>
            <TableCell><div>{{ item.last_success_at ? new Date(item.last_success_at).toLocaleString("uk-UA") : "Ещё не загружался" }}</div><div v-if="item.last_run_status" class="text-xs text-muted-foreground">{{ item.last_run_status }}</div></TableCell>
            <TableCell class="text-right">
              <DropdownMenu><DropdownMenuTrigger as-child><Button variant="ghost" size="icon" aria-label="Действия"><MoreHorizontal /></Button></DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem v-if="item.status === 'active'" @click="action.mutate({ id: item.id, action: 'sync' })">Загрузить сейчас</DropdownMenuItem>
                  <DropdownMenuItem v-if="item.status === 'active'" @click="action.mutate({ id: item.id, action: 'pause' })">Поставить на паузу</DropdownMenuItem>
                  <DropdownMenuItem v-if="item.status === 'paused'" @click="action.mutate({ id: item.id, action: 'resume' })">Возобновить</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>
</template>
