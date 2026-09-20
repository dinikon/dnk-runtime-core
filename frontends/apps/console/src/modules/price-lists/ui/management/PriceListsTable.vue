<script setup lang="ts">
import { MoreHorizontal } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PriceList } from "../../model/types";

defineProps<{ items: PriceList[] }>();
defineEmits<{ action: [item: PriceList, action: "sync" | "pause" | "resume" | "archive" | "restore"]; delete: [item: PriceList] }>();
const statusLabel: Record<string, string> = { draft: "Черновик", ready: "Готов", active: "Активен", paused: "На паузе", invalid: "Ошибка", archived: "Архив" };
</script>

<template>
  <div class="overflow-hidden rounded-lg border bg-background">
    <Table>
      <TableHeader><TableRow><TableHead>Название</TableHead><TableHead>Источник</TableHead><TableHead>Статус</TableHead><TableHead>Офферы</TableHead><TableHead>Следующая загрузка</TableHead><TableHead>Последняя загрузка</TableHead><TableHead><span class="sr-only">Действия</span></TableHead></TableRow></TableHeader>
      <TableBody>
        <TableRow v-for="item in items" :key="item.id">
          <TableCell><RouterLink class="font-medium hover:underline" :to="`/purchases/price-lists/${item.id}`">{{ item.title }}</RouterLink></TableCell>
          <TableCell><div class="uppercase">{{ item.source_format }}</div><div class="max-w-72 truncate text-xs text-muted-foreground">{{ item.source_url_display }}</div></TableCell>
          <TableCell><Badge :variant="item.status === 'active' ? 'secondary' : 'outline'">{{ statusLabel[item.status] }}</Badge></TableCell>
          <TableCell>{{ item.active_offer_count ?? 0 }}</TableCell>
          <TableCell>{{ item.next_sync_at ? new Date(item.next_sync_at).toLocaleString('uk-UA') : '—' }}</TableCell>
          <TableCell><div>{{ item.last_success_at ? new Date(item.last_success_at).toLocaleString('uk-UA') : 'Ещё не загружался' }}</div><div v-if="item.last_run_status" class="text-xs text-muted-foreground">{{ item.last_run_status }}</div></TableCell>
          <TableCell class="text-right">
            <DropdownMenu><DropdownMenuTrigger as-child><Button variant="ghost" size="icon" aria-label="Действия"><MoreHorizontal /></Button></DropdownMenuTrigger>
              <DropdownMenuContent align="end"><DropdownMenuGroup>
                <DropdownMenuItem v-if="item.status !== 'active' && item.status !== 'archived'" as-child><RouterLink :to="`/purchases/price-lists/${item.id}/edit`">Редактировать</RouterLink></DropdownMenuItem>
                <DropdownMenuItem v-if="item.status === 'active'" @click="$emit('action', item, 'sync')">Загрузить сейчас</DropdownMenuItem>
                <DropdownMenuItem v-if="item.status === 'active'" @click="$emit('action', item, 'pause')">Поставить на паузу</DropdownMenuItem>
                <DropdownMenuItem v-if="item.status === 'paused'" @click="$emit('action', item, 'resume')">Возобновить</DropdownMenuItem>
                <DropdownMenuItem v-if="item.status !== 'archived'" @click="$emit('action', item, 'archive')">Архивировать</DropdownMenuItem>
                <DropdownMenuItem v-if="item.status === 'archived'" @click="$emit('action', item, 'restore')">Восстановить</DropdownMenuItem>
                <DropdownMenuItem v-if="item.status === 'archived'" variant="destructive" @click="$emit('delete', item)">Удалить окончательно</DropdownMenuItem>
              </DropdownMenuGroup></DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </div>
</template>
