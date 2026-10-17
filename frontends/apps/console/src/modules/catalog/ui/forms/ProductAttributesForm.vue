<script setup lang="ts">
import { computed, ref } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CatalogAttribute } from "../../model/catalog.types";
import type { ProductAttribute } from "../../model/product.types";
import { useProductSectionDraft } from "../../model/use-product-section-draft";
import ProductReferencePicker from "./ProductReferencePicker.vue";
import ProductFieldError from "../product/ProductFieldError.vue";
const props = defineProps<{
  value: ProductAttribute[];
  attributes: CatalogAttribute[];
  disabled: boolean;
  reset: number;
  error?: string;
}>();
const emit = defineEmits<{ change: [value: ProductAttribute[]] }>();
const { value: assignments, change } = useProductSectionDraft(
  () => props.value,
  () => props.reset,
  (value) => emit("change", value),
);
const search = ref("");
const selected = ref("");
const available = computed(() =>
  props.attributes.filter(
    (a) =>
      !assignments.value.some((v) => v.attribute_id === a.id) &&
      (a.label ?? "Нет перевода")
        .toLocaleLowerCase()
        .includes(search.value.toLocaleLowerCase()),
  ),
);
function update(id: string, fields: Partial<ProductAttribute>): void {
  change(
    assignments.value.map((v) =>
      v.attribute_id === id ? { ...v, ...fields } : v,
    ),
  );
}
function add(): void {
  if (!available.value.some((a) => a.id === selected.value)) return;
  change([
    ...assignments.value,
    {
      attribute_id: selected.value,
      option_ids: [],
      visible: true,
      position: assignments.value.length,
    },
  ]);
  selected.value = "";
}
function remove(id: string): void {
  change(
    assignments.value
      .filter((v) => v.attribute_id !== id)
      .map((v, position) => ({ ...v, position })),
  );
}
</script>
<template>
  <fieldset
    :disabled="disabled"
    class="min-w-0"
    :aria-describedby="error ? 'attributes-error' : undefined"
  >
    <legend class="sr-only">Характеристики</legend>
    <FieldGroup class="gap-5">
      <Field
        v-for="assignment in assignments"
        :key="assignment.attribute_id"
        class="min-w-0 gap-3 rounded-lg border p-3"
        :data-invalid="!!error || undefined"
      >
        <ProductReferencePicker
          :label="
            attributes.find((a) => a.id === assignment.attribute_id)?.label ??
            'Нет перевода'
          "
          :ids="assignment.option_ids"
          :options="
            (
              attributes.find((a) => a.id === assignment.attribute_id)
                ?.options ?? []
            ).map((o) => ({ id: o.id, label: o.label ?? 'Нет перевода' }))
          "
          :disabled="disabled"
          @change="update(assignment.attribute_id, { option_ids: $event })"
        />
        <Field orientation="horizontal"
          ><FieldContent
            ><FieldLabel :for="`${assignment.attribute_id}-visible`"
              >Показывать характеристику</FieldLabel
            ></FieldContent
          ><label
            class="product-switch-target"
            :for="`${assignment.attribute_id}-visible`"
            ><Switch
              :id="`${assignment.attribute_id}-visible`"
              :model-value="assignment.visible"
              :disabled="disabled"
              @update:model-value="
                update(assignment.attribute_id, { visible: $event })
              " /></label></Field
        ><Button
          type="button"
          variant="ghost"
          class="min-h-11 self-start"
          :disabled="disabled"
          @click="remove(assignment.attribute_id)"
          >Убрать характеристику</Button
        >
      </Field>
      <Field
        ><FieldLabel for="attribute-search">Найти характеристику</FieldLabel
        ><Input
          id="attribute-search"
          v-model="search"
          placeholder="Поиск по названию"
      /></Field>
      <Field
        ><FieldLabel for="attribute-select">Добавить характеристику</FieldLabel
        ><Select v-model="selected" :disabled="disabled || !available.length"
          ><SelectTrigger id="attribute-select" class="w-full"
            ><SelectValue
              placeholder="Выберите характеристику" /></SelectTrigger
          ><SelectContent
            ><SelectGroup
              ><SelectItem
                v-for="attribute in available"
                :key="attribute.id"
                :value="attribute.id"
                >{{ attribute.label ?? "Нет перевода" }}</SelectItem
              ></SelectGroup
            ></SelectContent
          ></Select
        ></Field
      >
      <p v-if="!available.length" class="text-sm text-muted-foreground">
        {{
          attributes.length
            ? "Все характеристики добавлены или не подходят под поиск."
            : "Характеристики ещё не созданы."
        }}
      </p>
      <Button
        type="button"
        variant="outline"
        class="min-h-11"
        :disabled="disabled || !available.some((a) => a.id === selected)"
        @click="add"
        >Добавить характеристику</Button
      ><ProductFieldError id="attributes-error" :error="error" />
    </FieldGroup>
  </fieldset>
</template>
