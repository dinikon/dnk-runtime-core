<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { InternalMoveDocument } from "../../model/internal-move.types";
defineProps<{
  document: InternalMoveDocument | undefined;
  loading: boolean;
  error: string;
  disabled: boolean;
}>();
const emit = defineEmits<{ retry: [] }>();
</script>
<template>
  <section
    class="w-full max-w-5xl shrink-0 rounded-lg border bg-card p-4"
    aria-label="Основание перемещения"
  >
    <p
      v-if="loading && !document"
      role="status"
      class="text-sm text-muted-foreground"
    >
      Загрузка реквизитов документа…
    </p>
    <p v-if="error" role="alert" class="text-sm text-destructive">
      {{ error
      }}<Button
        type="button"
        variant="outline"
        :disabled="disabled"
        @click="emit('retry')"
        >Обновить реквизиты</Button
      >
    </p>
    <dl v-if="document" class="grid gap-3 text-sm sm:grid-cols-2">
      <div>
        <dt class="text-xs text-muted-foreground">Склад</dt>
        <dd class="break-words">
          {{ document.warehouseCode }} — {{ document.warehouseName }}
        </dd>
      </div>
      <div>
        <dt class="text-xs text-muted-foreground">Владелец товара</dt>
        <dd class="break-words">
          {{ document.ownerName ?? document.ownerId }}
        </dd>
      </div>
    </dl>
  </section>
</template>
