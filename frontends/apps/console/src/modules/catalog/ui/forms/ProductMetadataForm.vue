<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ProductMetadata } from "../../model/product.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import { decimalInput } from "../../model/product-input";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  value: ProductMetadata[];
  disabled: boolean;
  reset: number;
  error?: string;
}>();
const emit = defineEmits<{ change: [value: ProductMetadata[]] }>();
const { value: entries, change } = useProductSectionDraft(
  () => props.value,
  () => props.reset,
  (value) => emit("change", value),
);
function update(index: number, fields: Partial<ProductMetadata>): void {
  change(entries.value.map((v, i) => (i === index ? { ...v, ...fields } : v)));
}
function type(index: number, next: ProductMetadata["value_type"]): void {
  update(index, { value_type: next, value: next === "boolean" ? false : "" });
}
function remove(index: number): void {
  change(
    entries.value
      .filter((_, i) => i !== index)
      .map((v, position) => ({ ...v, position })),
  );
}
</script>
<template>
  <fieldset
    :disabled="disabled"
    class="min-w-0"
    :aria-describedby="error ? 'metadata-error' : undefined"
  >
    <legend class="sr-only">Дополнительные поля</legend>
    <FieldGroup class="gap-5">
      <FieldGroup
        v-for="(entry, index) in entries"
        :key="index"
        class="min-w-0 gap-3 rounded-lg border p-3"
      >
        <Field :data-invalid="!!error || undefined"
          ><FieldLabel :for="`metadata-${index}-key`">Ключ</FieldLabel
          ><Input
            :id="`metadata-${index}-key`"
            :model-value="entry.key"
            placeholder="Например, material"
            :aria-invalid="!!error || undefined"
            :aria-describedby="error ? 'metadata-error' : undefined"
            @update:model-value="update(index, { key: String($event) })"
        /></Field>
        <Field
          ><FieldLabel :for="`metadata-${index}-type`">Тип значения</FieldLabel
          ><Select
            :model-value="entry.value_type"
            :disabled="disabled"
            @update:model-value="
              type(index, $event as ProductMetadata['value_type'])
            "
            ><SelectTrigger :id="`metadata-${index}-type`" class="w-full"
              ><SelectValue /></SelectTrigger
            ><SelectContent
              ><SelectGroup
                ><SelectItem value="text">Текст</SelectItem
                ><SelectItem value="decimal">Число</SelectItem
                ><SelectItem value="boolean">Да / Нет</SelectItem></SelectGroup
              ></SelectContent
            ></Select
          ></Field
        >
        <Field
          :orientation="
            entry.value_type === 'boolean' ? 'horizontal' : 'vertical'
          "
          ><FieldLabel :for="`metadata-${index}-value`">Значение</FieldLabel
          ><label
            v-if="entry.value_type === 'boolean'"
            class="product-switch-target"
            :for="`metadata-${index}-value`"
            ><Switch
              :id="`metadata-${index}-value`"
              :model-value="entry.value === true"
              :disabled="disabled"
              @update:model-value="update(index, { value: $event })" /></label
          ><Input
            v-else
            :id="`metadata-${index}-value`"
            :model-value="String(entry.value)"
            :inputmode="entry.value_type === 'decimal' ? 'decimal' : 'text'"
            @update:model-value="
              update(index, {
                value:
                  entry.value_type === 'decimal'
                    ? decimalInput($event)
                    : String($event),
              })
            "
        /></Field>
        <Button
          type="button"
          variant="ghost"
          class="min-h-11 self-start"
          :disabled="disabled"
          @click="remove(index)"
          >Убрать поле</Button
        >
      </FieldGroup>
      <p v-if="!entries.length" class="text-sm text-muted-foreground">
        Дополнительные поля не заданы.
      </p>
      <Button
        type="button"
        variant="outline"
        class="min-h-11"
        :disabled="disabled"
        @click="
          change([
            ...entries,
            {
              key: '',
              value_type: 'text',
              value: '',
              position: entries.length,
            },
          ])
        "
        >Добавить поле</Button
      ><ProductFieldError id="metadata-error" :error="error" />
    </FieldGroup>
  </fieldset>
</template>
