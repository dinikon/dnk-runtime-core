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
import type { CatalogItem } from "../../model/catalog.types";
import type { ProductSection } from "../../model/product.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  item: CatalogItem;
  content: Record<string, string>;
  disabled: boolean;
  contentDisabled?: boolean;
  errors: Partial<Record<ProductSection, string>>;
  resets: Partial<Record<ProductSection, number>>;
}>();
const emit = defineEmits<{
  title: [value: string];
  save: [section: ProductSection, value: Record<string, unknown>];
}>();
const { value: sku, change: changeSku } = useProductSectionDraft(
  () => props.item.sku ?? "",
  () => props.resets.sku ?? 0,
  (value) => emit("save", "sku", { sku: value || null }),
);
const { value: virtual, change: changeVirtual } = useProductSectionDraft(
  () => props.item.virtual,
  () => props.resets.virtual ?? 0,
  (value) => emit("save", "virtual", { virtual: value }),
);
</script>
<template>
  <fieldset :disabled="disabled" class="min-w-0">
    <legend class="sr-only">Основные сведения</legend>
    <FieldGroup class="gap-5">
      <Field :data-invalid="!!errors.content || undefined">
        <FieldLabel :for="`${item.id}-title`"
          >Название <span aria-hidden="true">*</span></FieldLabel
        >
        <Input
          :id="`${item.id}-title`"
          data-product-title
          :model-value="content.title ?? ''"
          placeholder="Название товара"
          required
          :disabled="contentDisabled || disabled"
          maxlength="255"
          :aria-invalid="!!errors.content || undefined"
          :aria-describedby="
            errors.content ? `${item.id}-content-error` : undefined
          "
          @update:model-value="emit('title', String($event))"
        />
        <ProductFieldError
          :id="`${item.id}-content-error`"
          :error="errors.content"
        />
      </Field>
      <Field :data-invalid="!!errors.sku || undefined">
        <FieldLabel :for="`${item.id}-sku`">Артикул</FieldLabel>
        <Input
          :id="`${item.id}-sku`"
          :model-value="sku"
          placeholder="Например, CUP-001"
          maxlength="128"
          :aria-invalid="!!errors.sku || undefined"
          :aria-describedby="`${item.id}-sku-hint ${errors.sku ? `${item.id}-sku-error` : ''}`"
          @update:model-value="changeSku(String($event))"
        />
        <FieldDescription :id="`${item.id}-sku-hint`"
          >Уникальный артикул для поиска и учёта.</FieldDescription
        >
        <ProductFieldError :id="`${item.id}-sku-error`" :error="errors.sku" />
      </Field>
      <Field
        orientation="horizontal"
        :data-invalid="!!errors.virtual || undefined"
      >
        <FieldContent
          ><FieldLabel :for="`${item.id}-virtual`">Виртуальный товар</FieldLabel
          ><FieldDescription :id="`${item.id}-virtual-hint`"
            >Можно изменить в любой момент.</FieldDescription
          ></FieldContent
        >
        <label class="product-switch-target" :for="`${item.id}-virtual`"
          ><Switch
            :id="`${item.id}-virtual`"
            :model-value="virtual"
            :disabled="disabled"
            :aria-invalid="!!errors.virtual || undefined"
            :aria-describedby="`${item.id}-virtual-hint ${errors.virtual ? `${item.id}-virtual-error` : ''}`"
            @update:model-value="changeVirtual"
        /></label>
      </Field>
      <ProductFieldError
        :id="`${item.id}-virtual-error`"
        :error="errors.virtual"
      />
    </FieldGroup>
  </fieldset>
</template>
