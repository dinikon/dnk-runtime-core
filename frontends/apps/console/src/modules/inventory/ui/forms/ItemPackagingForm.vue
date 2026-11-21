<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type {
  ItemPackagingValues,
  ItemPackagingErrors,
  PackagingTypePickerState,
} from "../../model/item-packaging.types";
import type { InventoryUom } from "../../model/inventory-item-settings.types";
import ItemPackagingFields from "./ItemPackagingFields.vue";
withDefaults(
  defineProps<{
    prefix?: string;
    values: ItemPackagingValues;
    errors: ItemPackagingErrors;
    uoms: readonly InventoryUom[];
    picker: PackagingTypePickerState;
    pending: boolean;
    disabled: boolean;
    canSubmit: boolean;
    dirty: boolean;
  }>(),
  { prefix: "item-packaging" },
);
const emit = defineEmits<{
  change: [value: ItemPackagingValues];
  submit: [];
  reset: [];
  typeSearch: [value: string];
  typeOpen: [value: boolean];
  typeMore: [];
  typeRetry: [];
  typeRetrySelected: [];
}>();
</script>
<template>
  <form
    class="flex flex-col gap-6"
    novalidate
    :aria-busy="pending"
    @submit.prevent="emit('submit')"
  >
    <ItemPackagingFields
      :prefix="prefix"
      :values="values"
      :errors="errors"
      :uoms="uoms"
      :picker="picker"
      :disabled="disabled"
      @change="emit('change', $event)"
      @type-search="emit('typeSearch', $event)"
      @type-open="emit('typeOpen', $event)"
      @type-more="emit('typeMore')"
      @type-retry="emit('typeRetry')"
      @type-retry-selected="emit('typeRetrySelected')"
    />
    <slot name="feedback" />
    <slot name="actions"
      ><div class="flex flex-wrap gap-2">
        <Button
          type="submit"
          :disabled="disabled || pending || !canSubmit || !dirty"
          >{{ pending ? "Сохранение…" : "Сохранить" }}</Button
        >
        <Button
          type="button"
          variant="outline"
          :disabled="disabled || pending || !dirty"
          @click="emit('reset')"
          >Сбросить изменения</Button
        >
      </div></slot
    >
  </form>
</template>
