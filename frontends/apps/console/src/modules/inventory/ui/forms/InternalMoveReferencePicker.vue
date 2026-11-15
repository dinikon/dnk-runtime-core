<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { InternalMoveReferenceOption } from "../../model/internal-move.types";
defineProps<{
  label: string;
  search: string;
  items: readonly InternalMoveReferenceOption[];
  selectedId?: string;
  selectedName?: string;
  loading: boolean;
  error: string;
  offset: number;
  total: number;
  disabled: boolean;
  allowClear?: boolean;
}>();
const emit = defineEmits<{
  search: [v: string];
  select: [v: InternalMoveReferenceOption];
  page: [offset: number];
  retry: [];
  clear: [];
}>();
</script>
<template>
  <fieldset class="flex min-w-0 flex-col gap-2" :disabled="disabled">
    <legend class="mb-2 text-sm font-medium">{{ label }}</legend>
    <div
      v-if="selectedId"
      class="flex min-w-0 items-center justify-between gap-2 rounded-md bg-muted p-2 text-sm"
    >
      <span class="break-words"
        >Выбрано:
        {{
          selectedName ||
          items.find((item) => item.id === selectedId)?.name ||
          selectedId
        }}</span
      >
      ><Button
        v-if="allowClear"
        type="button"
        variant="ghost"
        size="sm"
        @click="emit('clear')"
        >Сбросить</Button
      >
    </div>
    <Input
      :model-value="search"
      type="search"
      :aria-label="`Поиск: ${label}`"
      autocomplete="off"
      @update:model-value="emit('search', String($event))"
    />
    <p v-if="loading" role="status" class="text-sm text-muted-foreground">
      Поиск…
    </p>
    <p v-else-if="error" role="alert" class="text-sm text-destructive">
      {{ error }}
      <Button type="button" variant="outline" size="sm" @click="emit('retry')"
        >Повторить поиск</Button
      >
    </p>
    <div v-else class="max-h-36 overflow-y-auto rounded-md border">
      <p v-if="!items.length" class="p-3 text-sm text-muted-foreground">
        Ничего не найдено.
      </p>
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="block w-full break-words px-3 py-2 text-left text-sm hover:bg-muted focus-visible:bg-muted"
        :aria-pressed="selectedId === item.id"
        @click="emit('select', item)"
      >
        {{ item.name
        }}<span v-if="selectedId === item.id" aria-hidden="true"> ✓</span>
      </button>
    </div>
    <div v-if="total > 20" class="flex flex-wrap items-center gap-2 text-xs">
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="loading || !offset"
        @click="emit('page', Math.max(0, offset - 20))"
        >Назад</Button
      ><span
        >{{ offset + 1 }}–{{ Math.min(offset + 20, total) }} из
        {{ total }}</span
      ><Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="loading || offset + 20 >= total"
        @click="emit('page', offset + 20)"
        >Далее</Button
      >
    </div>
  </fieldset>
</template>
