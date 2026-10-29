<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { ChevronDown } from "@lucide/vue";
import type { ProductPrice } from "../../model/product.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import { decimalInput } from "../../model/product-input";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  value: ProductPrice | null;
  reset: number;
  disabled: boolean;
  error?: string;
  current: string | null;
  id: string;
}>();
const emit = defineEmits<{ change: [value: ProductPrice | null] }>();
function emptyPrice(): ProductPrice {
  return {
    regular_price: "",
    currency: "UAH",
    sale_price: null,
    date_on_sale_from: null,
    date_on_sale_to: null,
  };
}
function hasPrice(value: ProductPrice): boolean {
  return !!(
    value.regular_price.trim() ||
    value.sale_price !== null ||
    value.date_on_sale_from ||
    value.date_on_sale_to
  );
}
const { value: price, change } = useProductSectionDraft(
  () => props.value ?? emptyPrice(),
  () => props.reset,
  (value) => emit("change", hasPrice(value) ? value : null),
);
const filled = computed(() => hasPrice(price.value));
const saleOpen = ref(!!props.value?.sale_price);
watch(
  () => props.error,
  (error) => {
    if (
      error &&
      (price.value.sale_price !== null ||
        price.value.date_on_sale_from ||
        price.value.date_on_sale_to)
    )
      saleOpen.value = true;
  },
);
function field<K extends keyof ProductPrice>(
  key: K,
  value: ProductPrice[K],
): void {
  change({ ...price.value, [key]: value });
}
function localDate(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
function dateField(
  key: "date_on_sale_from" | "date_on_sale_to",
  value: string | number,
): void {
  const date = new Date(value);
  field(
    key,
    !value || Number.isNaN(date.getTime()) ? null : date.toISOString(),
  );
}
</script>
<template>
  <fieldset
    :disabled="disabled"
    class="min-w-0"
    :aria-describedby="error ? `${id}-price-error` : undefined"
  >
    <legend class="sr-only">Цена</legend>
    <FieldGroup class="gap-3">
      <FieldGroup class="gap-3">
        <Field
          class="product-property-field"
          :data-invalid="!!error || undefined"
          ><FieldLabel :for="`${id}-regular-price`">Обычная цена</FieldLabel
          ><Input
            :id="`${id}-regular-price`"
            :model-value="price.regular_price"
            inputmode="decimal"
            placeholder="Не задана"
            :aria-invalid="!!error || undefined"
            :aria-describedby="error ? `${id}-price-error` : undefined"
            @update:model-value="field('regular_price', decimalInput($event))"
        /></Field>
        <Field class="product-property-field"
          ><FieldLabel :for="`${id}-currency`">Валюта</FieldLabel
          ><Input
            :id="`${id}-currency`"
            :model-value="price.currency"
            maxlength="3"
            required
            autocapitalize="characters"
            @update:model-value="
              field('currency', String($event).toUpperCase())
            "
        /></Field>
      </FieldGroup>
      <Collapsible v-model:open="saleOpen"
        ><CollapsibleTrigger
          class="group flex min-h-11 w-full items-center justify-between gap-2 text-left text-sm font-medium"
          >Акция
          <span
            v-if="price.sale_price !== null"
            class="ml-auto text-muted-foreground"
            >{{ price.sale_price }} {{ price.currency }}</span
          ><ChevronDown
            class="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" /></CollapsibleTrigger
        ><CollapsibleContent force-mount v-show="saleOpen" class="pt-3"
          ><FieldGroup class="gap-3">
            <Field
              ><FieldLabel :for="`${id}-sale-price`">Акционная цена</FieldLabel
              ><Input
                :id="`${id}-sale-price`"
                :model-value="price.sale_price ?? ''"
                inputmode="decimal"
                placeholder="Не задана"
                @update:model-value="
                  field('sale_price', decimalInput($event) || null)
                "
            /></Field>
            <FieldGroup class="grid min-w-0 grid-cols-1 gap-3"
              ><Field
                v-for="entry in [
                  {
                    key: 'date_on_sale_from' as const,
                    title: 'Начало акции',
                  },
                  { key: 'date_on_sale_to' as const, title: 'Конец акции' },
                ]"
                :key="entry.key"
                ><FieldLabel :for="`${id}-${entry.key}`">{{
                  entry.title
                }}</FieldLabel
                ><Input
                  :id="`${id}-${entry.key}`"
                  type="datetime-local"
                  :model-value="localDate(price[entry.key])"
                  @update:model-value="dateField(entry.key, $event)" /></Field
            ></FieldGroup> </FieldGroup></CollapsibleContent
      ></Collapsible>
      <ProductFieldError :id="`${id}-price-error`" :error="error" />
      <FieldDescription class="sr-only"
        >Подтверждённая цена: {{ current ?? "Не задана" }}
        {{ value?.currency }}</FieldDescription
      >
      <FieldDescription v-if="!filled"
        >Без цены товар недоступен для продажи.</FieldDescription
      >
    </FieldGroup>
  </fieldset>
</template>
