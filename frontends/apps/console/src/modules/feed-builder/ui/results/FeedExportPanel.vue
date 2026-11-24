<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import type {
  ExportIssueSeverity,
  FeedExportIssues,
  FeedExportState,
} from "../../model/feed-export.types";
import type { ExportFormat } from "../../model/feed.types";
import { feedValidationLabels } from "../../model/feed.constants";

const props = defineProps<{
  data: FeedExportState;
  configuredFormat?: ExportFormat;
  issues?: FeedExportIssues;
  issuesError: string;
  issuesLoading: boolean;
  severity: ExportIssueSeverity | "";
  offset: number;
  busy: boolean;
  error: string;
}>();
const emit = defineEmits<{
  refresh: [];
  rotate: [];
  copy: [url: string];
  filter: [severity: ExportIssueSeverity | ""];
  page: [offset: number];
  openPublication: [id: string];
  retryIssues: [];
}>();
const formatName = computed(() =>
  (props.data.active?.format ?? props.configuredFormat)?.toUpperCase(),
);
const pendingFormat = computed(() =>
  props.data.active && props.data.active.format !== props.configuredFormat
    ? props.configuredFormat?.toUpperCase()
    : undefined,
);
const reportTitle = computed(() => {
  const report = props.data.report;
  if (!report) return "";
  if (report.outcome === "PUBLISHED") return "Файл обновлён";
  if (report.outcome === "FAILED") {
    if (report.reasonCode === "CATEGORY_CONFIGURATION_INVALID")
      return "Проверьте настройки категорий и дерево Catalog";
    return report.reasonCode === "SOURCE_ACCESS_DENIED"
      ? "Доступ к данным Catalog отклонён"
      : "Сборка завершилась с технической ошибкой";
  }
  if (report.reasonCode === "FEED_CHANGED")
    return "Настройки фида изменились во время сборки";
  if (report.reasonCode === "FEED_INACTIVE")
    return "Фид больше недоступен для публикации";
  if (report.reasonCode === "ALL_ITEMS_REJECTED")
    return "Все позиции отклонены";
  return "Ошибки публикаций заблокировали обновление";
});
function dateLabel(value: string): string {
  return new Date(value).toLocaleString("ru-RU");
}
function selectSeverity(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  emit("filter", value === "ERROR" || value === "WARNING" ? value : "");
}
</script>
<template>
  <section class="grid min-w-0 gap-5" aria-label="Экспорт фида">
    <div class="grid min-w-0 gap-3 rounded-lg border p-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="font-medium">
          {{ formatName ? `Публичный ${formatName}` : "Публичная ссылка" }}
        </h2>
        <Button
          type="button"
          :disabled="busy || !!data.task || !data.canRefresh"
          @click="emit('refresh')"
        >
          Обновить фид
        </Button>
      </div>
      <p v-if="pendingFormat" class="text-sm text-muted-foreground">
        Формат следующей сборки — {{ pendingFormat }}.
      </p>
      <p v-if="data.task" role="status" class="text-sm text-muted-foreground">
        {{
          data.task.status === "RUNNING" ? "Фид собирается" : "Фид в очереди"
        }}
      </p>
      <p v-if="error" role="alert" class="text-sm text-destructive">
        {{ error }}
      </p>
      <template v-if="data.active">
        <dl class="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt class="text-muted-foreground">Данные на</dt>
            <dd>{{ dateLabel(data.active.asOf) }}</dd>
          </div>
          <div>
            <dt class="text-muted-foreground">Файл опубликован</dt>
            <dd>{{ dateLabel(data.active.publishedAt) }}</dd>
          </div>
        </dl>
        <a :href="data.active.url" class="break-all text-sm underline">{{
          data.active.url
        }}</a>
        <div class="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            @click="emit('copy', data.active.url)"
            >Скопировать ссылку</Button
          >
          <Button
            v-if="data.canRotate"
            type="button"
            size="sm"
            variant="outline"
            :disabled="busy"
            @click="emit('rotate')"
            >Заменить ссылку</Button
          >
        </div>
      </template>
      <p v-else class="text-sm text-muted-foreground">
        Ссылка появится после первой успешной сборки{{ formatName ? ` ${formatName}` : "" }}.
      </p>
    </div>
    <div v-if="data.report" class="grid min-w-0 gap-3 rounded-lg border p-4">
      <h2 class="font-medium">Последняя проверка</h2>
      <p class="text-sm">
        {{ reportTitle }} · {{ dateLabel(data.report.completedAt) }} ·
        {{ feedValidationLabels[data.report.validationPolicy] }}
      </p>
      <p
        v-if="data.report.outcome === 'PUBLISHED' && data.report.rejectedItems"
        class="text-sm"
      >
        В файл вошло {{ data.report.validItems + data.report.warningItems }} из
        {{ data.report.totalItems }} позиций. Пропущено {{ data.report.rejectedItems }}.
      </p>
      <p
        v-if="data.report.outcome !== 'PUBLISHED' && data.active"
        class="text-sm text-muted-foreground"
      >
        По ссылке доступен ранее опубликованный файл.
      </p>
      <p v-if="!data.report.isComplete" class="text-sm text-muted-foreground">
        Проверка завершилась досрочно.
      </p>
      <dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt class="text-muted-foreground">Всего</dt>
          <dd class="text-lg tabular-nums">{{ data.report.totalItems }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">Успешно</dt>
          <dd class="text-lg tabular-nums">{{ data.report.validItems }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">С предупреждениями</dt>
          <dd class="text-lg tabular-nums">{{ data.report.warningItems }}</dd>
        </div>
        <div>
          <dt class="text-muted-foreground">С ошибками</dt>
          <dd class="text-lg tabular-nums">{{ data.report.rejectedItems }}</dd>
        </div>
      </dl>
      <template v-if="data.report.warningItems || data.report.rejectedItems">
        <label class="flex flex-wrap items-center gap-2 text-sm">
          Диагностика
          <select
            class="rounded-md border bg-background p-1.5"
            :value="severity"
            @change="selectSeverity"
          >
            <option value="">Все</option>
            <option value="ERROR">Ошибки</option>
            <option value="WARNING">Предупреждения</option>
          </select>
        </label>
        <div v-if="issuesError" class="flex flex-wrap items-center gap-2">
          <p role="alert" class="text-sm text-destructive">{{ issuesError }}</p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            @click="emit('retryIssues')"
            >Повторить</Button
          >
        </div>
        <p
          v-else-if="issuesLoading"
          role="status"
          class="text-sm text-muted-foreground"
        >
          Загрузка диагностик…
        </p>
        <template v-else-if="issues">
          <p v-if="!issues.items.length" class="text-sm text-muted-foreground">
            Диагностик по выбранному фильтру нет.
          </p>
          <ul v-else class="grid gap-2">
            <li
              v-for="(issue, index) in issues.items"
              :key="index"
              class="min-w-0 rounded-md border p-2 text-sm"
            >
              <button
                type="button"
                class="max-w-full break-all text-left font-medium underline"
                @click="emit('openPublication', issue.publicationId)"
              >
                {{ issue.sku || "Открыть публикацию" }}
              </button>
              <span class="ml-2 text-muted-foreground">{{
                issue.severity === "ERROR" ? "Ошибка" : "Предупреждение"
              }}</span>
              <p class="break-words">{{ issue.message }}</p>
            </li>
          </ul>
          <div
            v-if="issues.total > 25 || offset"
            class="flex flex-wrap items-center gap-2"
          >
            <Button
              type="button"
              size="sm"
              variant="outline"
              :disabled="offset === 0"
              @click="emit('page', Math.max(0, offset - 25))"
              >Назад</Button
            >
            <Button
              type="button"
              size="sm"
              variant="outline"
              :disabled="offset + 25 >= issues.total"
              @click="emit('page', offset + 25)"
              >Далее</Button
            >
          </div>
        </template>
      </template>
    </div>
  </section>
</template>
