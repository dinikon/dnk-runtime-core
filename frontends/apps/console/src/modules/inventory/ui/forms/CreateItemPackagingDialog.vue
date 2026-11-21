<script setup lang="ts">
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type {
  ItemPackagingValues,
  ItemPackagingErrors,
  PackagingTypePickerState,
} from "../../model/item-packaging.types";
import type { InventoryUom } from "../../model/inventory-item-settings.types";
import ItemPackagingForm from "./ItemPackagingForm.vue";
defineProps<{
  open: boolean;
  values: ItemPackagingValues;
  errors: ItemPackagingErrors;
  uoms: readonly InventoryUom[];
  picker: PackagingTypePickerState;
  pending: boolean;
  disabled: boolean;
  canSubmit: boolean;
  uncertain: boolean;
  error: string;
}>();
const emit = defineEmits<{
  change: [value: ItemPackagingValues];
  submit: [];
  close: [];
  check: [];
  typeSearch: [value: string];
  typeOpen: [value: boolean];
  typeMore: [];
  typeRetry: [];
  typeRetrySelected: [];
}>();
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !pending && emit('close')">
    <DialogContent
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      :show-close-button="!pending"
      @escape-key-down="pending && $event.preventDefault()"
      @interact-outside="pending && $event.preventDefault()"
    >
      <DialogHeader
        ><DialogTitle>Создать упаковку</DialogTitle
        ><DialogDescription
          >Выберите тип тары и укажите количество и единицу содержимого этого
          SKU.</DialogDescription
        ></DialogHeader
      >
      <ItemPackagingForm
        prefix="item-packaging-create"
        :values="values"
        :errors="errors"
        :uoms="uoms"
        :picker="picker"
        :pending="pending"
        :disabled="disabled || pending || uncertain"
        :can-submit="canSubmit"
        :dirty="true"
        @change="emit('change', $event)"
        @submit="emit('submit')"
        @type-search="emit('typeSearch', $event)"
        @type-open="emit('typeOpen', $event)"
        @type-more="emit('typeMore')"
        @type-retry="emit('typeRetry')"
        @type-retry-selected="emit('typeRetrySelected')"
      >
        <template #feedback
          ><Alert v-if="error" variant="destructive"
            ><AlertDescription>{{ error }}</AlertDescription></Alert
          ></template
        >
        <template #actions
          ><DialogFooter class="gap-2"
            ><Button
              type="button"
              variant="outline"
              :disabled="pending"
              @click="emit('close')"
              >Отмена</Button
            ><Button
              v-if="uncertain"
              type="button"
              :disabled="disabled"
              @click="emit('check')"
              >Проверить список</Button
            ><Button
              v-else
              type="submit"
              :disabled="disabled || pending || !canSubmit"
              >{{ pending ? "Создание…" : "Создать" }}</Button
            ></DialogFooter
          ></template
        >
      </ItemPackagingForm>
    </DialogContent>
  </Dialog>
</template>
