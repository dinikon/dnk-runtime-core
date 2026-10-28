<script setup lang="ts">
import { computed } from "vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type { PublicationSyncRun } from "../model/publication.types";

const props = defineProps<{
  run: PublicationSyncRun | null;
  loading: boolean;
  disabled: boolean;
  error: string;
}>();
const labels: Record<string, string> = {
  queued: "Ожидает запуска",
  running: "Получаем публикации",
  completed: "Синхронизация завершена",
  failed: "Синхронизация остановлена",
  cancelled: "Синхронизация отменена",
};
const incomplete = computed(
  () =>
    !!props.run &&
    props.run.processedCount > 0 &&
    (props.run.recoveryRequired ||
      ["failed", "cancelled"].includes(props.run.status)),
);
</script>

<template>
  <div class="flex shrink-0 flex-col gap-2" data-slot="publication-sync-status">
    <div
      class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm"
      role="status"
    >
      <Badge
        :variant="run?.status === 'failed' ? 'destructive' : 'secondary'"
        >{{
          loading
            ? "Загружаем состояние…"
            : run
              ? labels[run.status]
              : "Публикации ещё не загружались"
        }}</Badge
      >
      <span v-if="run" class="tabular-nums text-muted-foreground"
        >Обработано: {{ run.processedCount }} · Пропущено:
        {{ run.skippedCount }}</span
      >
      <span v-if="disabled" class="text-muted-foreground"
        >Для запуска проверьте текущее подключение.</span
      >
    </div>
    <Alert
      v-if="error || run?.recoveryRequired || incomplete"
      :variant="error ? 'destructive' : 'default'"
    >
      <AlertDescription class="flex flex-col gap-1">
        <span v-if="error">{{ error }}</span>
        <span v-if="run?.recoveryRequired"
          >Выполнение прервано. Запустите синхронизацию снова.</span
        >
        <span v-if="incomplete"
          >Показаны полученные данные. Часть страниц этого запуска не
          загружена.</span
        >
      </AlertDescription>
    </Alert>
  </div>
</template>
