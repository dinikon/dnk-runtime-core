<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { InternalMoveDestination } from "../../model/internal-move-posting.types";
defineProps<{
  sourceLocationId: string | undefined;
  search: string;
  items: readonly InternalMoveDestination[];
  loading: boolean;
  error: string;
  offset: number;
  total: number;
}>();
const emit = defineEmits<{
  close: [];
  search: [value: string];
  select: [value: InternalMoveDestination];
  page: [offset: number];
  retry: [];
}>();
</script>
<template>
  <Dialog :open="true" @update:open="!$event && emit('close')"
    ><DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-xl"
      ><DialogHeader
        ><DialogTitle>Выбор локации назначения</DialogTitle
        ><DialogDescription
          >Выберите адрес в том же складе. Остальные измерения сохраняются из
          источника.</DialogDescription
        ></DialogHeader
      >
      <label class="text-sm"
        >Поиск локации назначения<Input
          :model-value="search"
          @update:model-value="emit('search', String($event))"
      /></label>
      <p v-if="loading" role="status">Загрузка позиций…</p>
      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ error
        }}<Button variant="outline" :disabled="loading" @click="emit('retry')"
          >Повторить</Button
        >
      </p>
      <p
        v-if="!loading && !error && !items.length"
        class="text-sm text-muted-foreground"
      >
        Допустимые локации назначения не найдены.
      </p>
      <div class="flex flex-col gap-2">
        <Button
          v-for="item in items"
          :key="item.id"
          variant="outline"
          class="h-auto justify-start whitespace-normal text-left"
          :disabled="loading || !!error || item.id === sourceLocationId"
          @click="emit('select', item)"
          ><span class="min-w-0 break-words"
            >{{ item.code }} — {{ item.name }}</span
          ></Button
        >
      </div>
      <div class="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          :disabled="loading || !offset"
          @click="emit('page', Math.max(0, offset - 20))"
          >Назад</Button
        ><span class="text-xs"
          >{{ total ? offset + 1 : 0 }}–{{ Math.min(offset + 20, total) }} из
          {{ total }}</span
        ><Button
          variant="outline"
          :disabled="loading || offset + 20 >= total"
          @click="emit('page', offset + 20)"
          >Далее</Button
        >
      </div>
    </DialogContent></Dialog
  >
</template>
