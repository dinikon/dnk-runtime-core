<script setup lang="ts">
import { ArrowUp, ArrowDown, Copy, Trash2, Plus } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import EmptyState from "@/components/custom-ui/empty-state/EmptyState.vue";
import type {
  SchemaFieldDraft,
  SchemaMetadata,
  SchemaIssue,
  FieldKind,
} from "../../model/feed-schema.types";
defineProps<{
  fields: SchemaFieldDraft[];
  totalFields: number;
  selectedId: string;
  metadata: SchemaMetadata;
  issues: SchemaIssue[];
  disabled: boolean;
  readonly: boolean;
  categories: boolean;
}>();
defineEmits<{
  select: [id: string];
  add: [kind: FieldKind];
  move: [id: string, delta: number];
  duplicate: [id: string];
  remove: [id: string];
}>();
</script>
<template>
  <section class="flex min-w-0 flex-col gap-4" :aria-label="categories ? 'Категории схемы' : 'Поля схемы'">
    <div v-if="!readonly" class="flex flex-wrap gap-2">
      <Button
        v-for="type in metadata.fieldTypes.filter((type) => (type.kind === 'category') === categories)"
        :key="type.kind"
        type="button"
        variant="outline"
        size="sm"
        :disabled="disabled || totalFields >= metadata.maxFields"
        @click="$emit('add', type.kind)"
        ><Plus data-icon="inline-start" />{{ type.label }}</Button
      >
    </div>
    <p class="text-sm text-muted-foreground">
      Полей в схеме {{ totalFields }} из {{ metadata.maxFields }}
    </p>
    <EmptyState
      v-if="!fields.length"
      :title="categories ? 'Категории пока не настроены' : 'В схеме пока нет полей предложения'"
      :description="
        readonly
          ? undefined
          : categories
            ? 'Добавьте категорию и настройте дерево фида.'
            : 'Добавьте поле нужного типа и выберите источник значения.'
      "
    />
    <ol v-else class="flex flex-col gap-2">
      <li
        v-for="(field, index) in fields"
        :key="field.id"
        class="flex min-w-0 flex-col gap-2 rounded-lg border p-3"
        :aria-current="selectedId === field.id ? 'true' : undefined"
      >
        <button
          type="button"
          class="flex min-w-0 items-start gap-2 rounded-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          :aria-pressed="selectedId === field.id"
          @click="$emit('select', field.id)"
        >
          <span class="shrink-0 text-sm text-muted-foreground"
            >{{ index + 1 }}.</span
          >
          <span class="flex min-w-0 flex-1 flex-col gap-1"
            ><span class="truncate font-medium">{{
              field.label || "Без подписи"
            }}</span
            ><span class="truncate text-xs text-muted-foreground"
              >{{ field.key || "Без ключа" }} ·
              {{
                metadata.fieldTypes.find(
                  (t) => t.kind === field.typeDefinition.kind,
                )?.label
              }}</span
            ></span
          >
          <Badge v-if="selectedId === field.id" variant="secondary"
            >Выбрано</Badge
          >
        </button>
        <p v-if="!field.export.enabled" class="text-xs text-muted-foreground">
          Исключено из экспорта
        </p>
        <p
          v-if="
            issues.some((i) => i.fieldId === field.id)
          "
          class="text-sm text-destructive"
        >
          Проверьте настройки поля
        </p>
        <div v-if="!readonly" class="flex flex-wrap gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled || index === 0"
            :aria-label="`Поднять поле ${field.label}`"
            @click="$emit('move', field.id, -1)"
            ><ArrowUp
          /></Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled || index === fields.length - 1"
            :aria-label="`Опустить поле ${field.label}`"
            @click="$emit('move', field.id, 1)"
            ><ArrowDown
          /></Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled || totalFields >= metadata.maxFields"
            :aria-label="`Дублировать поле ${field.label}`"
            @click="$emit('duplicate', field.id)"
            ><Copy
          /></Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            :disabled="disabled"
            :aria-label="`Удалить поле ${field.label}`"
            @click="$emit('remove', field.id)"
            ><Trash2
          /></Button>
        </div>
      </li>
    </ol>
  </section>
</template>
