<script setup lang="ts">
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { CounterpartyReference } from "@/modules/crm";
defineProps<{
  search: string;
  items: readonly CounterpartyReference[];
  selected: CounterpartyReference | null;
  loading: boolean;
  error: string;
  offset: number;
  total: number;
  disabled: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  select: [value: CounterpartyReference];
  page: [offset: number];
  retry: [];
}>();
</script>
<template>
  <fieldset class="flex min-w-0 flex-col gap-2" :disabled="disabled">
    <legend class="mb-2 text-sm font-medium">Контрагент поставщика</legend>
    <p v-if="selected" class="rounded-md bg-muted p-2 text-sm">
      Выбрано: <strong>{{ selected.name }}</strong>
    </p>
    <Input
      :model-value="search"
      type="search"
      aria-label="Поиск контрагента поставщика"
      placeholder="Найти компанию или контакт"
      autocomplete="off"
      @update:model-value="emit('search', String($event))"
    />
    <p v-if="loading" role="status" class="text-sm text-muted-foreground">
      Поиск контрагентов…
    </p>
    <div v-else-if="error" role="alert" class="text-sm text-destructive">
      {{ error }}
      <Button type="button" variant="outline" size="sm" @click="emit('retry')"
        >Повторить поиск</Button
      >
    </div>
    <div
      v-else
      class="max-h-44 overflow-auto rounded-md border"
      aria-label="Найденные контрагенты"
    >
      <p v-if="!items.length" class="p-3 text-sm text-muted-foreground">
        Контрагенты не найдены. Создайте запись в CRM или измените поиск.
      </p>
      <button
        v-for="counterparty in items"
        :key="`${counterparty.modelKey}:${counterparty.id}`"
        type="button"
        class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-muted focus-visible:bg-muted"
        :aria-pressed="
          counterparty.id === selected?.id && counterparty.modelKey === selected?.modelKey
        "
        @click="emit('select', counterparty)"
      >
        <span class="break-words">{{ counterparty.name }}</span
        ><span
          v-if="
            counterparty.id === selected?.id &&
            counterparty.modelKey === selected?.modelKey
          "
          aria-hidden="true"
          >✓</span
        >
      </button>
    </div>
    <div v-if="total > 20" class="flex items-center gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        :disabled="loading || !offset"
        @click="emit('page', Math.max(0, offset - 20))"
        >Назад</Button
      ><span class="text-xs text-muted-foreground"
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
