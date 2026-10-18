<script setup lang="ts">
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ProductStock } from "../../model/product.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import { stockLabels } from "../../model/product-presentation";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  value: ProductStock;
  reset: number;
  disabled: boolean;
  error?: string;
  current: string;
  id: string;
}>();
const emit = defineEmits<{ change: [value: ProductStock] }>();
const { value: stock, change } = useProductSectionDraft(
  () => props.value,
  () => props.reset,
  (value) => emit("change", value),
);
function managed(value: boolean): void {
  change(
    value
      ? {
          manage_stock: true,
          stock_quantity: 0,
          stock_status: null,
          backorders: "no",
        }
      : {
          manage_stock: false,
          stock_quantity: null,
          stock_status: "in_stock",
          backorders: "no",
        },
  );
}
function quantity(value: string | number): void {
  change({
    ...stock.value,
    stock_quantity: String(value).trim() ? Number(value) : null,
  });
}
</script>
<template>
  <fieldset :disabled="disabled" class="min-w-0">
    <legend class="sr-only">Наличие</legend>
    <FieldGroup class="gap-4">
      <Field orientation="horizontal"
        ><FieldContent
          ><FieldLabel :for="`${id}-manage-stock`"
            >Учитывать количество</FieldLabel
          ><FieldDescription
            >Или укажите наличие вручную.</FieldDescription
          ></FieldContent
        ><label class="product-switch-target" :for="`${id}-manage-stock`"
          ><Switch
            :id="`${id}-manage-stock`"
            :model-value="stock.manage_stock"
            :disabled="disabled"
            @update:model-value="managed" /></label
      ></Field>
      <Field v-if="stock.manage_stock" :data-invalid="!!error || undefined"
        ><FieldLabel :for="`${id}-quantity`">Количество</FieldLabel
        ><Input
          :id="`${id}-quantity`"
          :model-value="stock.stock_quantity ?? ''"
          type="number"
          inputmode="numeric"
          step="1"
          required
          :aria-invalid="!!error || undefined"
          :aria-describedby="error ? `${id}-stock-error` : undefined"
          @update:model-value="quantity"
      /></Field>
      <Field v-else
        ><FieldLabel :for="`${id}-stock-status`">Наличие</FieldLabel
        ><Select
          :model-value="stock.stock_status ?? 'in_stock'"
          :disabled="disabled"
          @update:model-value="
            change({
              ...stock,
              stock_status: $event as ProductStock['stock_status'],
            })
          "
          ><SelectTrigger :id="`${id}-stock-status`" class="w-full"
            ><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="(label, key) in stockLabels"
                :key="key"
                :value="key"
                >{{ label }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        ></Field
      >
      <Field v-if="stock.manage_stock"
        ><FieldLabel :for="`${id}-backorders`">Предзаказ</FieldLabel
        ><Select
          :model-value="stock.backorders"
          :disabled="disabled"
          @update:model-value="
            change({
              ...stock,
              backorders: $event as ProductStock['backorders'],
            })
          "
          ><SelectTrigger :id="`${id}-backorders`" class="w-full"
            ><SelectValue /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem value="no">Запрещён</SelectItem
              ><SelectItem value="notify">С уведомлением</SelectItem
              ><SelectItem value="yes">Разрешён</SelectItem></SelectGroup
            ></SelectContent
          ></Select
        ></Field
      >
      <ProductFieldError
        :id="`${id}-stock-error`"
        :error="error"
      /><FieldDescription
        >Подтверждённое наличие:
        {{ stockLabels[current] ?? "Не задано" }}</FieldDescription
      >
    </FieldGroup>
  </fieldset>
</template>
