<script setup lang="ts">
import { computed } from "vue";
import { Check, ChevronsUpDown, Star, X } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import {
  Combobox,
  ComboboxAnchor,
  ComboboxEmpty,
  ComboboxGroup,
  ComboboxInput,
  ComboboxItem,
  ComboboxItemIndicator,
  ComboboxList,
  ComboboxTrigger,
  ComboboxViewport,
} from "@/components/ui/combobox";
import type {
  CategoryOption,
  CategorySelection,
} from "../../model/category.types";
import {
  choosePrimary,
  withSelectedCategories,
} from "../../model/category-tree";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
const props = defineProps<{
  value: CategorySelection;
  options: CategoryOption[];
  reset: number;
  disabled: boolean;
  parentId: string | null;
  locale: string;
}>();
const emit = defineEmits<{ change: [value: CategorySelection] }>();
const { value: draft, change } = useProductSectionDraft(
  () => props.value,
  () => props.reset,
  (value) => emit("change", value),
);
const labels = computed(
  () => new Map(props.options.map((option) => [option.id, option.path])),
);
const selection = computed(() => (props.parentId ? props.value : draft.value));
const selectedIds = computed(() => [
  selection.value.primary_category_id,
  ...selection.value.additional_category_ids,
]);

function updateSelection(value: unknown): void {
  if (Array.isArray(value) && value.every((id) => typeof id === "string")) {
    change(withSelectedCategories(draft.value, value));
  }
}

function removeCategory(id: string): void {
  updateSelection(selectedIds.value.filter((selectedId) => selectedId !== id));
}
</script>
<template>
  <fieldset class="grid gap-3" :disabled="disabled">
    <template v-if="!parentId">
      <Combobox
        v-if="options.length"
        multiple
        :disabled="disabled"
        :model-value="selectedIds"
        :reset-search-term-on-select="false"
        @update:model-value="updateSelection"
      >
        <ComboboxAnchor class="w-full" as-child>
          <ComboboxTrigger as-child>
            <Button
              type="button"
              variant="outline"
              class="w-full justify-between font-normal"
            >
              Выбрать категории
              <ChevronsUpDown aria-hidden="true" class="opacity-50" />
            </Button>
          </ComboboxTrigger>
        </ComboboxAnchor>
        <ComboboxList
          align="start"
          class="w-[var(--reka-combobox-trigger-width)] max-w-[calc(100vw-2rem)]"
        >
          <ComboboxInput
            aria-label="Поиск категорий"
            placeholder="Название или путь категории"
          />
          <ComboboxEmpty class="px-3 py-4 text-muted-foreground">
            Категории не найдены.
          </ComboboxEmpty>
          <ComboboxViewport class="max-h-60 overflow-y-auto">
            <ComboboxGroup>
              <ComboboxItem
                v-for="option in options"
                :key="option.id"
                :value="option.id"
                :text-value="option.path"
                :disabled="option.id === selection.primary_category_id"
                :aria-disabled="
                  option.id === selection.primary_category_id || undefined
                "
              >
                <span class="min-w-0 flex-1 break-words">{{
                  option.path
                }}</span>
                <ComboboxItemIndicator>
                  <Check aria-hidden="true" />
                </ComboboxItemIndicator>
              </ComboboxItem>
            </ComboboxGroup>
          </ComboboxViewport>
        </ComboboxList>
      </Combobox>
      <p v-else role="status" class="text-sm text-muted-foreground">
        В каталоге пока нет категорий.
      </p>
    </template>

    <ul aria-label="Выбранные категории" class="grid gap-2">
      <li
        v-for="id in selectedIds"
        :key="id"
        class="flex min-w-0 items-center gap-2"
      >
        <span class="min-w-0 break-words text-sm">{{
          labels.get(id) ?? id
        }}</span>
        <Badge v-if="id === selection.primary_category_id" variant="secondary">
          Основная
        </Badge>
        <ButtonGroup
          v-else-if="!parentId"
          class="product-category-actions ml-auto shrink-0"
          :aria-label="`Действия с категорией: ${labels.get(id) ?? id}`"
        >
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            class="size-[24px]"
            :aria-label="`Сделать основной: ${labels.get(id) ?? id}`"
            title="Сделать основной"
            @click="change(choosePrimary(draft, id))"
          >
            <Star aria-hidden="true" class="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            class="size-[24px]"
            :aria-label="`Снять категорию: ${labels.get(id) ?? id}`"
            title="Снять категорию"
            @click="removeCategory(id)"
          >
            <X aria-hidden="true" class="size-3.5" />
          </Button>
        </ButtonGroup>
      </li>
    </ul>
    <RouterLink
      v-if="parentId"
      class="text-sm underline"
      :to="{
        path: '/catalog/items/' + parentId,
        query: { locale, tab: 'categories' },
      }"
      >Категории родительской карточки</RouterLink
    >
  </fieldset>
</template>
