<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableCaption,
} from "@/components/ui/table";
import {
  stockStatuses,
  stockActive,
  type BindingStock,
} from "../../model/stock.types";
import { stockCodeMessage } from "../../model/stock.errors";
import type { CatalogBinding } from "../../model/bindings/binding.types";
const props = defineProps<{
  group: CatalogBinding;
  state?: BindingStock;
  loading: boolean;
  error: string;
  busy: boolean;
  selected: string[];
}>();
const emit = defineEmits<{
  select: [ids: string[]];
  refresh: [];
  export: [];
  retry: [];
  repeat: [direction: "read" | "write", publicationId: string];
}>();
const availabilityLabels: Record<string, string> = {
  in_stock: "В наличии",
  out_of_stock: "Нет в наличии",
  on_order: "Предзаказ",
  removed: "Удалён из прайса",
  not_applicable: "Не применяется",
};
const active = computed(() => stockActive(props.state));
const selectedRows = computed(
  () =>
    props.state?.items.filter((v) =>
      props.selected.includes(v.publicationId),
    ) ?? [],
);
const canExport = computed(
  () =>
    selectedRows.value.length > 0 &&
    selectedRows.value.every((v) => !v.exportBlocker),
);
function choose(id: string, checked: boolean): void {
  emit(
    "select",
    checked
      ? [...new Set([...props.selected, id])]
      : props.selected.filter((v) => v !== id),
  );
}
function title(id: string): string {
  const p = props.group.preview.publications.find((v) => v.id === id);
  return p?.title ?? p?.externalId ?? id;
}
function received(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat("ru", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "Не обновлялся отдельно";
}
</script>
<template>
  <section
    class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4"
    :aria-busy="loading || busy || active"
  >
    <p class="text-sm text-muted-foreground">
      Получение обновляет только публикацию. Отправка использует количество
      Catalog и требует разрешения канала.
    </p>
    <Alert v-if="error" variant="destructive"
      ><AlertDescription
        >{{ error }}
        <Button type="button" variant="outline" size="sm" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <Skeleton v-if="loading && !state" class="h-24 w-full" />
    <template v-if="state">
      <Alert v-if="!state.allowStockExport"
        ><AlertDescription
          >Отправка остатков запрещена в настройках канала. Получение
          доступно.</AlertDescription
        ></Alert
      >
      <div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="busy || active || !state.items.length"
          @click="
            emit(
              'select',
              state.items.map((v) => v.publicationId),
            )
          "
          >Выбрать все</Button
        >
        <Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="busy || active || !selected.length"
          @click="emit('refresh')"
          >Обновить остаток</Button
        >
        <Button
          type="button"
          size="sm"
          :disabled="busy || active || !canExport"
          @click="emit('export')"
          >Отправить остаток</Button
        >
      </div>
      <p
        v-if="busy || active"
        role="status"
        class="text-sm text-muted-foreground"
      >
        Синхронизация выполняется…
      </p>
      <div class="min-w-0 overflow-x-auto">
        <Table class="min-w-[580px]">
          <TableCaption>Остатки связанных позиций</TableCaption>
          <TableHeader
            ><TableRow
              ><TableHead>Позиция</TableHead><TableHead>Catalog</TableHead
              ><TableHead>Площадка</TableHead
              ><TableHead>Состояние</TableHead></TableRow
            ></TableHeader
          >
          <TableBody
            ><TableRow v-for="item in state.items" :key="item.publicationId">
              <TableCell
                ><div class="flex items-start gap-2">
                  <Checkbox
                    :aria-label="`Выбрать ${title(item.publicationId)}`"
                    :model-value="selected.includes(item.publicationId)"
                    :disabled="busy || active"
                    @update:model-value="
                      choose(item.publicationId, $event === true)
                    "
                  /><span class="max-w-56 whitespace-normal">{{
                    title(item.publicationId)
                  }}</span>
                </div></TableCell
              >
              <TableCell class="tabular-nums"
                >{{ item.catalogQuantity ?? "Не учитывается" }}
                <p
                  v-if="item.catalogOwnerId !== item.catalogPositionId"
                  class="text-xs text-muted-foreground"
                >
                  Общий остаток родителя
                </p></TableCell
              >
              <TableCell class="tabular-nums"
                >{{ item.publicationQuantity ?? "Неизвестно" }}
                <p
                  v-if="item.publicationAvailability"
                  class="text-xs text-muted-foreground"
                >
                  {{
                    availabilityLabels[item.publicationAvailability] ??
                    item.publicationAvailability
                  }}
                </p>
                <p
                  v-if="item.ownerId !== item.publicationId"
                  class="text-xs text-muted-foreground"
                >
                  Общий остаток родителя
                </p>
                <p class="text-xs text-muted-foreground">
                  {{ received(item.operation?.observedAt ?? null) }}
                </p></TableCell
              >
              <TableCell class="max-w-64 whitespace-normal"
                ><p v-if="item.operation">
                  {{
                    item.operation.direction === "read"
                      ? "Получение"
                      : "Отправка"
                  }}: {{ stockStatuses[item.operation.status] }}
                </p>
                <p
                  v-if="item.operation?.errorCode"
                  role="alert"
                  class="text-sm text-destructive"
                >
                  {{ stockCodeMessage(item.operation.errorCode) }}
                </p>
                <Button
                  v-if="
                    item.operation &&
                    ['failed', 'cancelled'].includes(item.operation.status)
                  "
                  type="button"
                  variant="outline"
                  size="sm"
                  :disabled="
                    busy ||
                    active ||
                    (item.operation.direction === 'write' &&
                      !!item.exportBlocker)
                  "
                  @click="
                    emit('repeat', item.operation.direction, item.publicationId)
                  "
                  >Повторить действие</Button
                >
                <p
                  v-if="item.exportBlocker"
                  class="text-xs text-muted-foreground"
                >
                  {{ stockCodeMessage(item.exportBlocker) }}
                </p></TableCell
              >
            </TableRow></TableBody
          >
        </Table>
      </div>
    </template>
  </section>
</template>
