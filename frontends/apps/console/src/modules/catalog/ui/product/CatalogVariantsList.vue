<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import type { CatalogListItem } from "../../model/catalog.types";
import { statusLabels } from "../../model/product-presentation";
defineProps<{
  items: CatalogListItem[];
  pending: boolean;
  error: string;
  disabled: boolean;
}>();
const emit = defineEmits<{
  open: [id: string];
  remove: [id: string];
  retry: [];
}>();
</script>
<template>
  <div class="flex min-w-0 flex-col gap-3">
    <Alert v-if="error" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        >{{ error
        }}<Button variant="outline" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Skeleton v-if="pending" class="h-48 w-full" />
    <Table
      v-else-if="items.length"
      class="min-w-[560px]"
      aria-label="Варианты товара"
    >
      <TableHeader
        ><TableRow
          ><TableHead>Вариант</TableHead><TableHead>Цена</TableHead
          ><TableHead>Статус</TableHead
          ><TableHead
            ><span class="sr-only">Действия</span></TableHead
          ></TableRow
        ></TableHeader
      >
      <TableBody
        ><TableRow v-for="item in items" :key="item.id">
          <TableCell
            ><Button
              variant="link"
              class="h-auto whitespace-normal px-0 text-left"
              @click="emit('open', item.id)"
              >{{ item.title ?? "Без перевода" }}</Button
            >
            <p class="text-xs text-muted-foreground">
              {{ item.sku ?? item.id }}
            </p></TableCell
          >
          <TableCell>{{
            item.price === null
              ? "Не задана"
              : item.price + " " + (item.currency ?? "")
          }}</TableCell>
          <TableCell>{{ statusLabels[item.status] }}</TableCell>
          <TableCell class="text-right"
            ><Button
              variant="ghost"
              :disabled="disabled"
              @click="emit('remove', item.id)"
              >Удалить</Button
            ></TableCell
          >
        </TableRow></TableBody
      >
    </Table>
    <p
      v-else-if="!error"
      class="py-8 text-center text-sm text-muted-foreground"
    >
      Вариантов пока нет. Добавьте первую продаваемую позицию.
    </p>
  </div>
</template>
