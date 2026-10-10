<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import ProductStructureForm from "./ProductStructureForm.vue";
import type {
  ProductType,
  CatalogAttribute,
  ProductKind,
  ProductStructureDraft,
} from "../../model/catalog.types";
defineProps<{
  types: ProductType[];
  attributes: CatalogAttribute[];
  pending: boolean;
  disabled: boolean;
}>();
const emit = defineEmits<{
  submit: [typeId: string, structure: ProductStructureDraft];
  dirty: [value: boolean];
}>();
const typeId = ref(""),
  kind = ref<ProductKind>("simple"),
  virtual = ref(false);
watch([typeId, kind, virtual], () => emit("dirty", true));
</script>
<template>
  <div class="space-y-5">
    <fieldset :disabled="pending" class="space-y-4">
      <label class="block space-y-2"
        ><span>Вид товара</span
        ><select
          v-model="kind"
          aria-label="Вид товара"
          class="w-full rounded-md border bg-background p-2"
        >
          <option value="simple">SIMPLE</option>
          <option value="variable">VARIABLE</option>
        </select></label
      >
      <label class="block space-y-2"
        ><span>Тип контента</span
        ><select
          v-model="typeId"
          aria-label="Тип контента"
          class="w-full rounded-md border bg-background p-2"
        >
          <option value="">Default</option>
          <option v-for="type in types" :key="type.id" :value="type.id">
            {{ type.label ?? type.code }}
          </option>
        </select></label
      >
    </fieldset>
    <form
      v-if="kind === 'simple'"
      class="space-y-4"
      @submit.prevent="
        $emit('submit', typeId, {
          kind: 'simple',
          variant: { id: null, virtual, selection: {} },
        })
      "
    >
      <p class="text-sm text-muted-foreground">
        SIMPLE — одна продаваемая позиция. Переводы заполняются после создания.
      </p>
      <label class="flex items-center gap-2"
        ><input
          v-model="virtual"
          type="checkbox"
          :disabled="pending"
        />Виртуальная позиция</label
      >
      <Button type="submit" :disabled="pending || disabled">{{
        pending ? "Создание…" : "Создать товар"
      }}</Button>
    </form>
    <ProductStructureForm
      v-else
      :initial="null"
      :attributes="attributes"
      target-kind="variable"
      :pending="pending"
      :disabled="disabled"
      :reset="0"
      @dirty="$emit('dirty', true)"
      @submit="$emit('submit', typeId, $event)"
    />
    <p class="text-sm text-muted-foreground">
      SKU и файлы требуют подключения смежных модулей.
    </p>
  </div>
</template>
