<script setup lang="ts">
import { ChevronDown, Pencil, Image } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { VariantRowModel } from "../../model/product.types";
defineProps<{
  row: VariantRowModel;
  selected: boolean;
  editing?: boolean;
  dirty?: boolean;
}>();
defineEmits<{ select: []; edit: [] }>();
</script>
<template>
  <div
    class="flex flex-wrap items-center gap-4 border-b py-4 last:border-0"
    :class="selected ? 'bg-muted/30' : ''"
  >
    <div
      class="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted/20"
    >
      <img
        v-if="row.image"
        :src="row.image"
        alt=""
        class="size-full object-cover"
      /><Image v-else class="size-5 text-muted-foreground" />
    </div>
    <button
      type="button"
      class="flex min-w-0 flex-1 flex-col items-start gap-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
      :aria-expanded="editing ? selected : undefined"
      :aria-pressed="editing ? undefined : selected"
      @click="$emit('select')"
    >
      <span class="break-words text-sm font-medium"
        >{{ row.label }}
        <span v-if="dirty" aria-label="Есть несохранённые изменения"
          >•</span
        ></span
      ><span class="text-xs text-muted-foreground">{{
        row.item.own.sku ?? "Артикул не задан"
      }}</span>
    </button>
    <div class="flex flex-col gap-1 text-sm">
      <span class="font-medium">{{ row.price }}</span
      ><span class="text-xs text-muted-foreground">{{ row.stock }}</span>
    </div>
    <Badge variant="outline">{{ row.status }}</Badge>
    <Button
      v-if="editing"
      variant="ghost"
      size="icon"
      :aria-label="`Раскрыть ${row.label}`"
      @click="$emit('select')"
      ><ChevronDown :class="selected ? 'rotate-180' : ''" /></Button
    ><Button v-else variant="outline" size="sm" @click="$emit('edit')"
      ><Pencil data-icon="inline-start" />Редактировать</Button
    >
  </div>
</template>
