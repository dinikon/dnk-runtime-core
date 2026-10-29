<script setup lang="ts">
import { Check, LoaderCircle, MoreHorizontal } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import { statusLabels } from "../../model/product-labels";
import type { ProductStatus } from "../../model/product.types";
import ProductFieldError from "./ProductFieldError.vue";
const props = defineProps<{
  id: string;
  status: ProductStatus;
  reset: number;
  disabled: boolean;
  pending: boolean;
  saved: boolean;
  saveStatus: string;
  error?: string;
}>();
const emit = defineEmits<{ status: [value: ProductStatus]; reload: [] }>();
const { value: status, change } = useProductSectionDraft(
  () => props.status,
  () => props.reset,
  (value) => emit("status", value),
);
</script>
<template>
  <div class="flex min-w-0 flex-col gap-1 border-b px-4 py-2">
    <div class="flex items-center justify-between gap-2">
      <FieldGroup class="w-32 shrink-0"
        ><Field orientation="horizontal" :data-invalid="!!error || undefined">
          <FieldLabel :for="`${id}-status`" class="sr-only"
            >Статус товара</FieldLabel
          >
          <Select
            :model-value="status"
            :disabled="disabled"
            @update:model-value="change($event as ProductStatus)"
          >
            <SelectTrigger
              :id="`${id}-status`"
              class="w-full"
              :aria-invalid="!!error || undefined"
              :aria-describedby="error ? `${id}-status-error` : undefined"
              ><SelectValue
            /></SelectTrigger>
            <SelectContent
              ><SelectGroup
                ><SelectItem
                  v-for="(label, key) in statusLabels"
                  :key="key"
                  :value="key"
                  >{{ label }}</SelectItem
                ></SelectGroup
              ></SelectContent
            >
          </Select>
        </Field></FieldGroup
      >
      <div class="ml-auto flex items-center gap-1">
        <slot name="actions" /><DropdownMenu
          ><DropdownMenuTrigger as-child
            ><Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Действия с товаром"
              ><MoreHorizontal /></Button></DropdownMenuTrigger
          ><DropdownMenuContent align="end"
            ><DropdownMenuGroup
              ><DropdownMenuItem :disabled="pending" @select="emit('reload')"
                >Обновить данные товара</DropdownMenuItem
              ></DropdownMenuGroup
            ></DropdownMenuContent
          ></DropdownMenu
        >
      </div>
    </div>
    <p
      role="status"
      aria-live="polite"
      data-testid="autosave-status"
      class="flex items-center gap-2 text-xs text-muted-foreground"
    >
      <LoaderCircle
        v-if="pending"
        class="size-3.5 shrink-0 animate-spin"
        aria-hidden="true"
      /><Check
        v-else-if="saved"
        class="size-3.5 shrink-0"
        aria-hidden="true"
      />{{ saveStatus }}
    </p>
    <ProductFieldError :id="`${id}-status-error`" :error="error" />
  </div>
</template>
