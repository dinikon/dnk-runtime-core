<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

defineProps<{
  open: boolean;
  items: { fileId: string; name: string }[];
  loading: boolean;
  error: string;
  search: string;
  page: number;
  total: number;
}>();
const emit = defineEmits<{
  close: [];
  search: [value: string];
  page: [page: number];
  pick: [fileId: string];
  retry: [];
}>();
</script>

<template>
  <Dialog :open="open" @update:open="!$event && emit('close')"
    ><DialogContent class="flex max-h-[85dvh] flex-col"
      ><DialogHeader
        ><DialogTitle>Изображения для представления</DialogTitle
        ><DialogDescription
          >Выберите готовый файл своего рабочего
          пространства.</DialogDescription
        ></DialogHeader
      ><Input
        :model-value="search"
        aria-label="Поиск изображения"
        placeholder="Название файла"
        @update:model-value="emit('search', String($event))"
      />
      <p v-if="loading" role="status">Загрузка изображений…</p>
      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ error }}
        <Button type="button" variant="outline" size="sm" @click="emit('retry')"
          >Повторить</Button
        >
      </p>
      <ul class="min-h-0 space-y-2 overflow-y-auto">
        <li
          v-for="image in items"
          :key="image.fileId"
          class="flex min-w-0 items-center justify-between gap-3 rounded-md border p-3"
        >
          <span class="min-w-0 break-words text-sm">{{ image.name }}</span
          ><Button
            type="button"
            variant="outline"
            size="sm"
            @click="emit('pick', image.fileId)"
            >Добавить</Button
          >
        </li>
      </ul>
      <p
        v-if="!loading && !error && !items.length"
        class="text-sm text-muted-foreground"
      >
        Подходящих изображений нет.
      </p>
      <div v-if="total > 25" class="flex justify-between gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="page <= 1 || loading"
          @click="emit('page', page - 1)"
          >Назад</Button
        ><Button
          type="button"
          variant="outline"
          :disabled="page * 25 >= total || loading"
          @click="emit('page', page + 1)"
          >Далее</Button
        >
      </div></DialogContent
    ></Dialog
  >
</template>
