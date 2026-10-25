<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  importStatusLabels,
  importIsActive,
} from "../../model/import.constants";
import type { CatalogImportRun } from "../../model/import.types";
const props = defineProps<{ run: CatalogImportRun; pending: boolean }>();
defineEmits<{ cancel: []; report: [] }>();
const progress = computed(() =>
  props.run.total
    ? Math.round((props.run.processed / props.run.total) * 100)
    : 0,
);
</script>
<template>
  <div class="flex flex-col gap-5" aria-live="polite">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <Badge variant="secondary">{{ importStatusLabels[run.status] }}</Badge>
        <h3 class="mt-3 text-lg font-semibold">
          Обработано {{ run.processed }} из {{ run.total }}
        </h3>
      </div>
      <span class="text-2xl font-semibold tabular-nums">{{ progress }}%</span>
    </div>
    <Progress :model-value="progress" aria-label="Прогресс импорта" />
    <dl class="grid grid-cols-2 gap-4 sm:grid-cols-5">
      <div
        v-for="[label, count] in [
          ['Создано', run.created],
          ['Обновлено', run.updated],
          ['Пропущено', run.skipped],
          ['Ошибки', run.errors],
          ['Предупреждения', run.warnings],
        ]"
        :key="label"
      >
        <dt class="text-sm text-muted-foreground">{{ label }}</dt>
        <dd class="mt-1 text-xl font-semibold tabular-nums">{{ count }}</dd>
      </div>
    </dl>
    <Alert v-if="run.error" variant="destructive"
      ><AlertTitle>Импорт не завершён</AlertTitle
      ><AlertDescription>{{ run.error }}</AlertDescription></Alert
    >
    <p v-if="importIsActive(run.status)" class="text-sm text-muted-foreground">
      Можно закрыть окно. Импорт продолжится, а его результат будет доступен в
      журнале.
    </p>
    <div class="flex flex-wrap justify-end gap-3">
      <Button
        v-if="['queued', 'running', 'cancelling'].includes(run.status)"
        variant="outline"
        :disabled="pending || run.status === 'cancelling'"
        @click="$emit('cancel')"
        >{{
          run.status === "cancelling"
            ? "Остановка после текущей позиции…"
            : "Остановить импорт"
        }}</Button
      ><Button variant="outline" :disabled="pending" @click="$emit('report')"
        >Скачать отчёт CSV</Button
      >
    </div>
  </div>
</template>
