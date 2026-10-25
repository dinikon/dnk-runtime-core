<script setup lang="ts">
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ImportRowsPage } from "../../model/import.types";
defineProps<{
  data: ImportRowsPage | undefined;
  loading: boolean;
  error: string;
  page: number;
  outcome: string;
}>();
defineEmits<{
  page: [value: number];
  outcome: [value: string];
  retry: [];
  item: [id: string];
}>();
const labels: Record<string, string> = {
  pending: "Ожидает",
  created: "Создан",
  updated: "Обновлён",
  skipped: "Пропущен",
  errors: "Ошибка",
};
</script>
<template>
  <section class="flex min-w-0 flex-col gap-3" aria-label="Результаты записей">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h3 class="font-semibold">Результаты записей</h3>
      <Select
        :model-value="outcome || 'all'"
        @update:model-value="
          (v) => $emit('outcome', v === 'all' ? '' : String(v))
        "
        ><SelectTrigger class="w-48" aria-label="Фильтр результатов"
          ><SelectValue /></SelectTrigger
        ><SelectContent
          ><SelectGroup
            ><SelectItem value="all">Все записи</SelectItem
            ><SelectItem value="errors">С ошибками</SelectItem
            ><SelectItem value="warnings">С предупреждениями</SelectItem
            ><SelectItem value="skipped">Пропущенные</SelectItem
            ><SelectItem value="created">Созданные</SelectItem
            ><SelectItem value="updated">Обновлённые</SelectItem></SelectGroup
          ></SelectContent
        ></Select
      >
    </div>
    <p v-if="error" role="alert">
      {{ error }}
      <Button variant="outline" size="sm" @click="$emit('retry')"
        >Повторить</Button
      >
    </p>
    <p v-else-if="loading && !data" class="text-sm text-muted-foreground">
      Загрузка результатов…
    </p>
    <template v-else>
      <ul
        class="flex flex-col divide-y rounded-lg border sm:hidden"
        aria-label="Результаты товаров"
      >
        <li
          v-for="row in data?.items ?? []"
          :key="row.number"
          class="flex min-w-0 flex-col gap-2 p-3"
        >
          <div class="flex min-w-0 items-center justify-between gap-3">
            <div class="flex min-w-0 items-center gap-2">
              <span class="text-xs text-muted-foreground"
                >{{ row.number }}.</span
              ><Button
                v-if="row.itemId"
                variant="link"
                class="h-auto min-w-0 truncate p-0"
                @click="$emit('item', row.itemId)"
                >{{ row.sku || "Открыть товар" }}</Button
              ><span v-else class="truncate text-sm font-medium">{{
                row.sku || "Без SKU"
              }}</span>
            </div>
            <span class="shrink-0 text-xs">{{
              labels[row.outcome] || row.outcome
            }}</span>
          </div>
          <p
            v-for="message in row.errors"
            :key="message"
            class="break-words text-sm text-destructive"
          >
            {{ message }}
          </p>
          <p
            v-for="message in row.warnings"
            :key="message"
            class="break-words text-xs text-muted-foreground"
          >
            {{ message }}
          </p>
        </li>
        <li
          v-if="!data?.items.length"
          class="p-5 text-center text-sm text-muted-foreground"
        >
          Записей с выбранным результатом пока нет.
        </li>
      </ul>
      <div class="hidden overflow-x-auto rounded-lg border sm:block">
        <Table
          ><TableHeader
            ><TableRow
              ><TableHead>№</TableHead><TableHead>SKU</TableHead
              ><TableHead>Результат</TableHead
              ><TableHead>Подробности</TableHead></TableRow
            ></TableHeader
          ><TableBody
            ><TableRow v-for="row in data?.items ?? []" :key="row.number"
              ><TableCell>{{ row.number }}</TableCell
              ><TableCell
                ><Button
                  v-if="row.itemId"
                  variant="link"
                  class="h-auto p-0"
                  @click="$emit('item', row.itemId)"
                  >{{ row.sku || "Открыть товар" }}</Button
                ><span v-else>{{ row.sku || "—" }}</span></TableCell
              ><TableCell>{{ labels[row.outcome] || row.outcome }}</TableCell
              ><TableCell class="min-w-52 whitespace-normal"
                ><p
                  v-for="message in [...row.errors, ...row.warnings]"
                  :key="message"
                >
                  {{ message }}
                </p></TableCell
              ></TableRow
            ><TableRow v-if="!data?.items.length"
              ><TableCell
                :colspan="4"
                class="p-6 text-center text-muted-foreground"
                >Записей с выбранным результатом пока нет.</TableCell
              ></TableRow
            ></TableBody
          ></Table
        >
      </div>
    </template>
    <div class="flex items-center justify-end gap-3">
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1"
        @click="$emit('page', page - 1)"
        >Назад</Button
      ><span class="text-sm"
        >{{ page }} /
        {{ Math.max(1, Math.ceil((data?.total ?? 0) / 50)) }}</span
      ><Button
        variant="outline"
        size="sm"
        :disabled="page * 50 >= (data?.total ?? 0)"
        @click="$emit('page', page + 1)"
        >Далее</Button
      >
    </div>
  </section>
</template>
