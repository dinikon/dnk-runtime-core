<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import type { BatchExportOverview } from "../model/batch-export.types";
import {
  batchActive,
  batchStatusLabels,
  exportReason,
  scheduleDateLabel,
} from "../model/batch-export.presentation";
import { dateLabel } from "../model/channels.presentation";
import ExportScheduleForm from "./ExportScheduleForm.vue";
defineProps<{
  overview: BatchExportOverview;
  pending: boolean;
  archived: boolean;
  error: string | null;
  saveSequence: number;
}>();
defineEmits<{
  start: [mode: "provider" | "file"];
  outbound: [enabled: boolean];
  open: [runId: string];
  schedule: [
    value: {
      enabled: boolean;
      hour: number;
      minute: number;
      timezone: string;
      expectedRevision: number;
    },
  ];
  dirty: [value: boolean];
}>();
</script>
<template>
  <Card>
    <CardHeader
      ><div class="flex flex-wrap items-start justify-between gap-3">
        <div class="flex flex-col gap-2">
          <CardTitle>Пакетное обновление текстов</CardTitle
          ><CardDescription
            >Названия и описания на языках подключения берём из каталога. Каждый
            запуск готовит один файл для всего разрешённого
            состава.</CardDescription
          >
        </div>
        <Badge variant="outline">{{
          overview.outboundEnabled
            ? "Синхронизация разрешена"
            : "Синхронизация выключена"
        }}</Badge>
      </div></CardHeader
    >
    <CardContent class="flex flex-col gap-5">
      <Alert v-if="!overview.feedAvailable"
        ><AlertTitle>Выгрузка недоступна</AlertTitle
        ><AlertDescription
          >Проверьте активный домен тенанта и настройки подписи выгрузок на
          сервере.</AlertDescription
        ></Alert
      >
      <Alert v-else-if="!overview.deliveryConfigured"
        ><AlertTitle>XML можно проверить локально</AlertTitle
        ><AlertDescription
          >Сформируйте файл и откройте ссылку в результате. Для автоматической
          отправки нужен публичный домен тенанта: источник не может скачать файл
          с localhost.</AlertDescription
        ></Alert
      >
      <Alert v-if="error" variant="destructive"
        ><AlertDescription>{{ error }}</AlertDescription></Alert
      >
      <p class="text-muted-foreground text-sm">
        Связано с каталогом: {{ overview.boundCount }}. Экспорт разрешён:
        {{ overview.enabledCount }}. Публикации без уникального ключа, полных
        текстов или с неподдерживаемым статусом будут пропущены.
      </p>
      <div class="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          :disabled="
            pending ||
            archived ||
            !overview.feedAvailable ||
            !overview.outboundEnabled ||
            !overview.enabledCount ||
            overview.recent.some((run) => batchActive(run.status))
          "
          @click="$emit('start', 'file')"
          >Сформировать XML</Button
        >
        <Button
          :disabled="
            pending ||
            archived ||
            !overview.deliveryConfigured ||
            !overview.outboundEnabled ||
            !overview.enabledCount ||
            overview.recent.some((run) => batchActive(run.status))
          "
          @click="$emit('start', 'provider')"
          >{{ pending ? "Подождите…" : "Обновить сейчас" }}</Button
        ><Button
          variant="outline"
          :disabled="pending || archived"
          @click="$emit('outbound', !overview.outboundEnabled)"
          >{{
            overview.outboundEnabled
              ? "Выключить синхронизацию"
              : "Разрешить синхронизацию"
          }}</Button
        >
      </div>
      <ExportScheduleForm
        :schedule="overview.schedule"
        :pending="pending"
        :disabled="archived"
        :allow-daily="overview.deliveryConfigured"
        :save-sequence="saveSequence"
        @submit="(value) => $emit('schedule', value)"
        @dirty="(value) => $emit('dirty', value)"
      />
      <p class="text-muted-foreground text-sm">
        {{
          overview.schedule.nextAt
            ? `Следующий запуск: ${scheduleDateLabel(overview.schedule.nextAt, overview.schedule.timezone)} · ${overview.schedule.timezone}`
            : "Ежедневный запуск выключен"
        }}. При выключенной синхронизации новый пакет не отправляется.
      </p>
      <section
        class="flex flex-col gap-3"
        aria-label="История пакетных обновлений"
      >
        <h3 class="text-sm font-medium">Последние обновления</h3>
        <p v-if="!overview.recent.length" class="text-muted-foreground text-sm">
          Обновлений пока не было.
        </p>
        <div
          v-for="run in overview.recent"
          :key="run.id"
          class="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3"
        >
          <div class="flex min-w-0 flex-col gap-1">
            <span class="text-sm font-medium">{{
              batchStatusLabels[run.status]
            }}</span
            ><span class="text-muted-foreground text-xs"
              >{{ dateLabel(run.createdAt) }} ·
              {{ run.trigger === "daily" ? "По расписанию" : "Вручную" }} ·
              {{
                run.deliveryMode === "file"
                  ? `в XML ${run.counts.ready ?? 0}`
                  : `подтверждено ${run.counts.verified ?? 0}`
              }}, пропущено {{ run.counts.skipped ?? 0 }}</span
            ><span
              v-if="run.errorCode"
              class="text-destructive max-w-xl text-xs"
              >{{ exportReason(run.errorCode) }}</span
            >
          </div>
          <Button variant="outline" size="sm" @click="$emit('open', run.id)"
            >Результат / XML</Button
          >
        </div>
      </section>
    </CardContent>
  </Card>
</template>
