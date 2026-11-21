<script setup lang="ts">
import { ref, watch } from "vue";
import {
  Combobox,
  ComboboxAnchor,
  ComboboxInput,
  ComboboxList,
  ComboboxGroup,
  ComboboxItem,
} from "@/components/ui/combobox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { StockLocation } from "../../model/stock-location.types";
const props = defineProps<{
  id: string;
  label: string;
  emptyLabel: string;
  search: string;
  options: readonly StockLocation[];
  total: number;
  loading: boolean;
  fetchingMore: boolean;
  hasMore: boolean;
  error: string;
  selectedId: string | null;
  selected?: StockLocation;
  selectedLoading: boolean;
  selectedError: string;
  disabled?: boolean;
  invalid?: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  select: [id: string | null];
  open: [value: boolean];
  more: [];
  retry: [];
  retrySelected: [];
}>();
const open = ref(false);
watch(open, (value) => emit("open", value));
watch(
  () => props.disabled,
  (value) => {
    if (value) open.value = false;
  },
);
function choose(id: string | null): void {
  if (props.disabled) return;
  emit("select", id);
  open.value = false;
}
</script>
<template>
  <div class="flex min-w-0 flex-col gap-2">
    <Combobox
      v-model:open="open"
      :model-value="selectedId"
      ignore-filter
      open-on-focus
      open-on-click
      :reset-search-term-on-blur="false"
      :reset-search-term-on-select="false"
      :disabled="disabled"
    >
      <ComboboxAnchor class="w-full rounded-md border"
        ><ComboboxInput
          :id="id"
          :model-value="search"
          :disabled="disabled"
          :aria-label="label"
          :aria-invalid="invalid"
          placeholder="Найти по коду или названию"
          @update:model-value="emit('search', String($event))"
      /></ComboboxAnchor>
      <ComboboxList
        class="w-(--reka-combobox-trigger-width) max-w-[calc(100vw-2rem)]"
      >
        <div class="max-h-64 overflow-y-auto">
          <p
            v-if="loading"
            role="status"
            class="p-3 text-sm text-muted-foreground"
          >
            Поиск локаций…
          </p>
          <p v-if="error" role="alert" class="p-3 text-sm text-destructive">
            {{ error }}
          </p>
          <ComboboxGroup>
            <ComboboxItem value="__none__" @select="choose(null)">{{
              emptyLabel
            }}</ComboboxItem>
            <ComboboxItem
              v-for="option in options"
              :key="option.id"
              :value="option.id"
              :disabled="loading"
              @select="choose(option.id)"
            >
              <span class="min-w-0 flex-1"
                ><span class="block break-all font-mono">{{ option.code }}</span
                ><span
                  class="block break-words text-xs text-muted-foreground"
                  >{{ option.name }}</span
                ></span
              >
              <Badge v-if="!option.isActive" variant="outline">Неактивна</Badge>
            </ComboboxItem>
            <ComboboxItem
              v-if="hasMore"
              value="__more__"
              :disabled="loading || fetchingMore"
              @select.prevent="emit('more')"
              >{{ fetchingMore ? "Загрузка…" : "Загрузить ещё" }}</ComboboxItem
            >
          </ComboboxGroup>
          <p
            v-if="!loading && !error && !options.length"
            class="p-3 text-sm text-muted-foreground"
          >
            Локации не найдены.
          </p>
          <p
            v-if="options.length"
            class="px-3 pb-2 text-xs text-muted-foreground"
          >
            Показано {{ options.length }} из {{ total }}
          </p>
        </div>
      </ComboboxList>
    </Combobox>
    <div
      v-if="selectedId"
      class="flex min-w-0 flex-wrap items-center gap-2 text-sm"
    >
      <span v-if="selected" class="min-w-0 flex-1 break-words"
        ><span class="font-mono break-all">{{ selected.code }}</span> —
        {{ selected.name }}</span
      >
      <span
        v-else-if="selectedLoading"
        role="status"
        class="text-muted-foreground"
        >Загрузка выбранной локации…</span
      >
      <span v-else-if="!selectedError" class="text-muted-foreground"
        >Загрузка выбранной локации…</span
      >
      <Button
        type="button"
        variant="ghost"
        size="sm"
        :disabled="disabled"
        @click="choose(null)"
        >{{ emptyLabel }}</Button
      >
    </div>
    <p v-else class="text-xs text-muted-foreground">{{ emptyLabel }}</p>
    <Alert v-if="selectedError" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-2"
        ><span>{{ selectedError }}</span
        ><Button
          type="button"
          variant="outline"
          size="sm"
          :disabled="disabled || selectedLoading"
          @click="emit('retrySelected')"
          >Повторить загрузку родителя</Button
        ></AlertDescription
      ></Alert
    >
    <Button
      v-if="error"
      type="button"
      variant="outline"
      size="sm"
      :disabled="disabled || loading || fetchingMore"
      @click="emit('retry')"
      >Повторить поиск локаций</Button
    >
  </div>
</template>
