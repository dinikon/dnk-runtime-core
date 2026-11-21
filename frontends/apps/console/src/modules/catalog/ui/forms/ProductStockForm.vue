<script setup lang="ts">
import { computed } from "vue";
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
import { stockLabels, stockFormMode } from "../../model/product-presentation";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  value: ProductStock;
  kind?: "simple" | "variable" | "variant";
  parentStock?: ProductStock;
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
const mode = computed(() =>
  stockFormMode(props.kind ?? "simple", stock.value, props.parentStock),
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
    <FieldGroup class="gap-3">
      <Field orientation="horizontal"
        ><FieldContent
          ><FieldLabel :for="`${id}-manage-stock`">{{
            kind === "variant"
              ? "Учитывать собственное количество"
              : kind === "variable"
                ? "Учитывать общее количество"
                : "Учитывать количество"
          }}</FieldLabel
          ><FieldDescription class="sr-only">{{
            kind === "variable"
              ? "Общее количество для вариантов без собственного учёта."
              : kind === "variant"
                ? "Без собственного учёта используется общее количество или ручное наличие."
                : "Или укажите наличие вручную."
          }}</FieldDescription></FieldContent
        ><label class="product-switch-target" :for="`${id}-manage-stock`"
          ><Switch
            :id="`${id}-manage-stock`"
            :model-value="stock.manage_stock"
            :disabled="disabled"
            @update:model-value="managed" /></label
      ></Field>
      <Field
        class="product-property-field"
        v-if="stock.manage_stock"
        :data-invalid="!!error || undefined"
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
      <Field class="product-property-field" v-else-if="mode === 'manual'"
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
      <FieldDescription v-if="mode === 'variants'"
        >Наличие задаётся в вариантах.</FieldDescription
      >
      <FieldDescription v-if="mode === 'inherited'" role="status">
        Используется общее количество карточки:
        {{ parentStock?.stock_quantity }}. Включите собственный учёт, чтобы
        задать количество этого варианта.
      </FieldDescription>
      <Field class="product-property-field" v-if="stock.manage_stock"
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
      /><FieldDescription class="sr-only" v-if="mode !== 'variants'"
        >Подтверждённое наличие:
        {{ stockLabels[current] ?? "Не задано" }}</FieldDescription
      >
    </FieldGroup>
  </fieldset>
</template>
