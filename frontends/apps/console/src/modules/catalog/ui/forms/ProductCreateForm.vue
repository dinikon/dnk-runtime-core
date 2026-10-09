<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import type { ProductType } from "../../model/catalog.types";
defineProps<{ types: ProductType[]; pending: boolean; disabled: boolean }>();
const emit = defineEmits<{
  submit: [typeId: string, virtual: boolean];
  dirty: [value: boolean];
}>();
const typeId = ref(""),
  virtual = ref(false);
watch([typeId, virtual], () => emit("dirty", true));
</script>
<template>
  <form class="space-y-5" @submit.prevent="$emit('submit', typeId, virtual)">
    <p class="text-sm text-muted-foreground">
      SIMPLE — одна продаваемая позиция. Переводы заполняются после создания.
    </p>
    <label class="block space-y-2"
      ><span>Тип контента</span
      ><select
        v-model="typeId"
        aria-label="Тип контента"
        class="block w-full rounded-md border bg-background p-2"
        :disabled="pending"
      >
        <option value="">Default / Чистый</option>
        <option v-for="type in types" :key="type.id" :value="type.id">
          {{ type.label ?? type.code }}
        </option>
      </select></label
    ><label class="flex gap-2"
      ><input
        v-model="virtual"
        type="checkbox"
        :disabled="pending"
      />Виртуальная позиция</label
    >
    <p class="text-sm text-muted-foreground">
      VARIABLE появится после справочника осей. SKU и файлы требуют подключения
      смежных модулей.
    </p>
    <Button type="submit" :disabled="pending || disabled">{{
      pending ? "Создание…" : "Создать товар"
    }}</Button>
  </form>
</template>
