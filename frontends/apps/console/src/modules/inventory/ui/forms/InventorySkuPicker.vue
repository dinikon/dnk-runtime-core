<script setup lang="ts">
import { computed, ref } from "vue";
import { Plus, X } from "@lucide/vue";
import {
  Combobox,
  ComboboxAnchor,
  ComboboxInput,
  ComboboxList,
  ComboboxItem,
} from "@/components/ui/combobox";
import { Button } from "@/components/ui/button";
import type { InventorySkuOption } from "../../model/inventory-sku.types";

const props = defineProps<{
  id: string;
  search: string;
  options: readonly InventorySkuOption[];
  loading: boolean;
  error: string;
  total: number;
  selectedCode?: string | null;
  selectedId?: string | null;
  disabled?: boolean;
  pending?: boolean;
}>();
const emit = defineEmits<{
  search: [value: string];
  select: [value: InventorySkuOption];
  create: [sku: string];
  clear: [];
  retry: [];
}>();
const open = ref(false);
const code = computed(() => props.search.trim());
const canCreate = computed(
  () =>
    !!code.value &&
    !props.loading &&
    !props.error &&
    !props.options.some((option) => option.sku === code.value),
);
function choose(value: unknown): void {
  if (props.disabled || props.pending || props.loading) return;
  if (value === "create" && canCreate.value) emit("create", code.value);
  else {
    const option = props.options.find((option) => option.id === value);
    if (option) emit("select", option);
  }
  open.value = false;
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2" :aria-busy="pending">
    <Combobox
      v-model:open="open"
      :model-value="selectedId ?? null"
      ignore-filter
      open-on-focus
      open-on-click
      :reset-search-term-on-blur="false"
      :reset-search-term-on-select="false"
      :disabled="disabled || pending"
    >
      <ComboboxAnchor class="w-full rounded-md border">
        <ComboboxInput
          :id="id"
          :model-value="search"
          :disabled="disabled || pending"
          placeholder="Найти или создать SKU"
          aria-label="Поиск SKU"
          :aria-describedby="`${id}-hint`"
          @update:model-value="emit('search', String($event))"
        />
      </ComboboxAnchor>
      <ComboboxList
        class="w-(--reka-combobox-trigger-width) max-w-[calc(100vw-2rem)]"
      >
        <div class="max-h-64 overflow-y-auto p-1">
          <p
            v-if="loading"
            role="status"
            class="p-3 text-sm text-muted-foreground"
          >
            Поиск SKU…
          </p>
          <p
            v-else-if="error"
            role="alert"
            class="p-3 text-sm text-destructive"
          >
            {{ error }}
          </p>
          <template v-else>
            <ComboboxItem
              v-for="option in options"
              :key="option.id"
              :value="option.id"
              :disabled="pending"
              @select="choose(option.id)"
            >
              <span class="min-w-0 flex-1 break-all font-mono">{{
                option.sku
              }}</span>
              <span class="text-xs text-muted-foreground">{{
                option.baseUom
              }}</span>
            </ComboboxItem>
            <p v-if="!options.length" class="p-3 text-sm text-muted-foreground">
              SKU не найдены.
            </p>
            <ComboboxItem
              v-if="canCreate"
              value="create"
              :disabled="pending"
              class="border-t"
              @select="choose('create')"
            >
              <Plus aria-hidden="true" /><span class="min-w-0 break-all"
                >Создать SKU «{{ code }}»</span
              >
            </ComboboxItem>
            <p
              v-if="total > options.length"
              class="p-3 text-xs text-muted-foreground"
            >
              Показаны первые {{ options.length }} из {{ total }}. Уточните код.
            </p>
          </template>
        </div>
      </ComboboxList>
    </Combobox>
    <div
      v-if="selectedCode"
      class="flex min-w-0 items-center justify-between gap-2 text-sm"
    >
      <span class="min-w-0 break-all"
        >SKU: <span class="font-mono">{{ selectedCode }}</span></span
      >
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Очистить связь SKU"
        :disabled="disabled || pending"
        @click="emit('clear')"
        ><X aria-hidden="true"
      /></Button>
    </div>
    <p :id="`${id}-hint`" class="text-xs text-muted-foreground">
      Выберите складскую позицию или создайте код до 25 символов. Новая позиция:
      PCS, шаг 1.
    </p>
    <p v-if="pending" role="status" class="text-sm text-muted-foreground">
      Сохранение SKU…
    </p>
    <Button
      v-if="error"
      type="button"
      variant="outline"
      size="sm"
      :disabled="loading || disabled || pending"
      @click="emit('retry')"
      >Повторить поиск SKU</Button
    >
  </div>
</template>
