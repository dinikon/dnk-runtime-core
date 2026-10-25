<script setup lang="ts">
import { ref } from "vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import SalesFeedback from "./SalesFeedback.vue";
import type { SaleSummary } from "../../model/sales.types";
import type { FunnelStage } from "@/modules/funnel";
export interface SalesColumn {
  stage: FunnelStage;
  items: SaleSummary[];
  total: number | null;
  loading: boolean;
  error: string;
  fetching: boolean;
}
const props = defineProps<{
  view: "kanban" | "list";
  columns: SalesColumn[];
  items: SaleSummary[];
  stages: FunnelStage[];
  contactNames: Record<string, string>;
  companyNames: Record<string, string>;
  movingId: string;
  busy: boolean;
  filtered: boolean;
  fetching: boolean;
  total: number;
  offset: number;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{
  open: [record: SaleSummary];
  move: [record: SaleSummary];
  drop: [record: SaleSummary, stageId: string];
  more: [stageId: string];
  retry: [stageId?: string];
  page: [page: number];
}>();
const dragging = ref<SaleSummary | null>(null);
function hint(item: SaleSummary) {
  if (item.kind === "leads")
    return (
      [item.lastName, item.firstName, item.companyName]
        .filter(Boolean)
        .join(" · ") ||
      [
        ...item.contactIds.map(
          (id) => props.contactNames[id] ?? "Связанный контакт",
        ),
        ...item.companyIds.map(
          (id) => props.companyNames[id] ?? "Связанная компания",
        ),
      ].join(" · ") ||
      "Контакт не указан"
    );
  const values = [
    ...item.contactIds.map((id) => props.contactNames[id] ?? "Контакт"),
    ...item.companyIds.map((id) => props.companyNames[id] ?? "Компания"),
  ];
  return (
    values.slice(0, 2).join(" · ") +
      (values.length > 2 ? " · ещё " + (values.length - 2) : "") ||
    [item.firstName, item.lastName, item.companyName]
      .filter(Boolean)
      .join(" · ") ||
    "Участники не указаны"
  );
}
function drop(stageId: string) {
  if (dragging.value) emit("drop", dragging.value, stageId);
  dragging.value = null;
}
function stageName(id: string) {
  return props.stages.find((s) => s.id === id)?.name ?? "Стадия";
}
function stageColor(color: string): string {
  return (
    (
      {
        blue: "bg-blue-500",
        green: "bg-green-500",
        amber: "bg-amber-500",
        red: "bg-red-500",
        violet: "bg-violet-500",
      } as Record<string, string>
    )[color] ?? "bg-muted-foreground"
  );
}
</script>
<template>
  <div
    v-if="view === 'kanban'"
    class="flex min-h-64 flex-col gap-4 overflow-x-auto pb-4 sm:flex-row"
    aria-label="Канбан"
  >
    <section
      v-for="column in columns"
      :key="column.stage.id"
      class="flex w-full shrink-0 sm:w-72 flex-col gap-3 rounded-lg bg-muted/40 p-3"
      :aria-label="column.stage.name"
      @dragover.prevent
      @drop.prevent="drop(column.stage.id)"
    >
      <header class="flex items-center justify-between gap-2">
        <h2 class="flex items-center gap-2 break-words font-medium">
          <span
            aria-hidden="true"
            class="size-2 shrink-0 rounded-full"
            :class="stageColor(column.stage.color)"
          />{{ column.stage.name }}
        </h2>
        <span
          v-if="column.fetching && !column.loading"
          role="status"
          class="text-xs text-muted-foreground"
          >Обновляем…</span
        ><Badge variant="secondary">{{ column.total ?? "…" }}</Badge>
      </header>
      <p
        v-if="column.error && column.items.length"
        role="alert"
        class="text-sm text-destructive"
      >
        {{ column.error }}
        <Button variant="link" @click="emit('retry', column.stage.id)"
          >Повторить</Button
        >
      </p>
      <SalesFeedback
        :loading="column.loading"
        :error="column.items.length ? '' : column.error"
        :empty="!column.items.length"
        :empty-title="filtered ? 'Нет совпадений' : 'Нет карточек'"
        empty-description="В этой стадии пока нет подходящих записей."
        @retry="emit('retry', column.stage.id)"
        ><Card v-for="item in column.items" :key="item.id" class="gap-3 py-4"
          ><CardHeader class="px-4"
            ><CardTitle class="text-base"
              ><button
                class="break-words text-left hover:underline focus-visible:outline-ring"
                @click="emit('open', item)"
              >
                {{ item.title }}
              </button></CardTitle
            ><CardDescription class="break-words">{{
              hint(item)
            }}</CardDescription></CardHeader
          ><CardContent class="px-4"
            ><p class="font-medium">{{ item.total }} {{ item.currency }}</p>
            <Badge v-if="item.conversionResult" variant="outline"
              >Конвертирован</Badge
            ></CardContent
          ><CardFooter class="flex flex-wrap gap-2 px-4"
            ><Button size="sm" variant="outline" @click="emit('open', item)"
              >Открыть</Button
            ><Button
              size="sm"
              variant="ghost"
              :disabled="!!item.conversionResult || busy"
              @click="emit('move', item)"
              >{{
                movingId === item.id ? "Перемещаем…" : "Переместить"
              }}</Button
            ><button
              v-if="!item.conversionResult"
              type="button"
              draggable="true"
              class="cursor-grab rounded p-2 text-muted-foreground focus-visible:outline-ring"
              :disabled="busy"
              :aria-label="'Перетащить ' + item.title"
              @dragstart="
                dragging = item;
                $event.dataTransfer?.setData('text/plain', item.id);
              "
              @dragend="dragging = null"
            >
              ⠿
            </button></CardFooter
          ></Card
        ></SalesFeedback
      >
      <div class="flex flex-col gap-2">
        <p v-if="column.total !== null" class="text-xs text-muted-foreground">
          Показано {{ column.items.length }} из {{ column.total }}
        </p>
        <Button
          v-if="column.total !== null && column.items.length < column.total"
          variant="outline"
          :disabled="column.fetching"
          @click="emit('more', column.stage.id)"
          >{{ column.fetching ? "Загружаем…" : "Загрузить ещё" }}</Button
        >
      </div>
    </section>
  </div>
  <SalesFeedback
    v-else
    :loading="loading"
    :error="items.length ? '' : error"
    :empty="!items.length"
    :empty-title="filtered ? 'Нет совпадений' : 'Карточек пока нет'"
    :empty-description="
      filtered
        ? 'Измените поиск или фильтры.'
        : 'Создайте первую карточку, чтобы начать работу.'
    "
    @retry="emit('retry')"
    ><div class="flex flex-col gap-4">
      <p
        v-if="error && items.length"
        role="alert"
        class="text-sm text-destructive"
      >
        {{ error }}
        <Button variant="link" @click="emit('retry')">Повторить</Button>
      </p>
      <p v-if="fetching" role="status" class="text-sm text-muted-foreground">
        Обновляем список…
      </p>
      <div class="overflow-auto rounded-lg border">
        <Table
          ><TableHeader
            ><TableRow
              ><TableHead>Название</TableHead
              ><TableHead>Клиент / участники</TableHead
              ><TableHead>Стадия</TableHead><TableHead>Сумма</TableHead
              ><TableHead>Изменено</TableHead
              ><TableHead>Действия</TableHead></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow v-for="item in items" :key="item.id"
              ><TableCell
                ><button
                  class="font-medium hover:underline"
                  @click="emit('open', item)"
                >
                  {{ item.title }}</button
                ><Badge v-if="item.conversionResult" variant="outline"
                  >Конвертирован</Badge
                ></TableCell
              ><TableCell>{{ hint(item) }}</TableCell
              ><TableCell>{{ stageName(item.stageId) }}</TableCell
              ><TableCell class="whitespace-nowrap"
                >{{ item.total }} {{ item.currency }}</TableCell
              ><TableCell>{{
                new Date(item.updatedAt).toLocaleString()
              }}</TableCell
              ><TableCell
                ><Button
                  variant="ghost"
                  size="sm"
                  :disabled="!!item.conversionResult || busy"
                  @click="emit('move', item)"
                  >Переместить</Button
                ></TableCell
              ></TableRow
            ></TableBody
          ></Table
        >
      </div>
      <div class="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          :disabled="offset === 0"
          @click="emit('page', Math.floor(offset / 20))"
          >Назад</Button
        >
        <p class="text-sm text-muted-foreground">
          {{ offset + 1 }}–{{ offset + items.length }} из {{ total }}
        </p>
        <Button
          variant="outline"
          :disabled="offset + items.length >= total"
          @click="emit('page', Math.floor(offset / 20) + 2)"
          >Далее</Button
        >
      </div>
    </div></SalesFeedback
  >
</template>
