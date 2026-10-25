<script setup lang="ts">
import { computed } from "vue";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  importStatusLabels,
  importIsActive,
} from "../../model/import.constants";
import type { CatalogImportRun } from "../../model/import.types";
const props = defineProps<{ run: CatalogImportRun; pending: boolean }>();
const progress = computed(() =>
  props.run.total
    ? Math.round((props.run.processed / props.run.total) * 100)
    : 0,
);
</script>
<template>
  <div class="flex flex-col gap-5" aria-live="polite">
    <div class="flex flex-col gap-2">
      <h3 class="text-xl font-semibold tracking-tight">
        {{
          run.status === "cancelled"
            ? "Импорт остановлен"
            : importStatusLabels[run.status]
        }}
      </h3>
      <p v-if="run.canResume" class="text-sm text-muted-foreground">
        Продолжим с первой необработанной записи. Готовые товары и настройки
        сохранятся.
      </p>
      <p
        v-else-if="run.status === 'cancelled'"
        class="text-sm text-muted-foreground"
      >
        Продолжение недоступно: источник не подготовлен или срок его хранения
        истёк. Создайте новый импорт.
      </p>
    </div>
    <div class="flex items-end justify-between gap-3">
      <p class="text-2xl font-semibold tabular-nums">
        {{ run.processed }}
        <span class="text-base font-normal text-muted-foreground"
          >из {{ run.total }}</span
        >
      </p>
      <span class="text-2xl font-semibold tabular-nums">{{ progress }}%</span>
    </div>
    <Progress :model-value="progress" aria-label="Прогресс импорта" />
    <dl
      class="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-5"
    >
      <div
        v-for="[label, count] in [
          ['Создано', run.created],
          ['Обновлено', run.updated],
          ['Пропущено', run.skipped],
          ['Ошибки', run.errors],
          ['Предупреждения', run.warnings],
        ]"
        :key="label"
        class="bg-background p-4 last:col-span-2 sm:last:col-span-1"
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
  </div>
</template>
