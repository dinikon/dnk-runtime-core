<script setup lang="ts">
import { ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field";
import type { FeedImport } from "../../model/content-feed.types";
import {
  feedSubmissionLabel,
  feedReportLabel,
  feedVerificationLabel,
  feedFieldLabel,
  feedFieldStatus,
  feedDate,
} from "../../model/content-feed.display";
import { contentFeedIssue } from "../../model/content-feed.errors";
const props = defineProps<{
  operation: FeedImport | null;
  busy: boolean;
  ready: boolean;
  enabled: boolean;
  verified: boolean;
  publicationLinks: Record<string, string>;
}>();
const emit = defineEmits<{
  start: [force: boolean];
  resume: [];
  attach: [id: string];
  resolve: [];
  refresh: [];
}>();
const reviewed = ref(false),
  force = ref(false),
  externalId = ref(""),
  confirmedAbsent = ref(false);
watch(
  () => props.operation?.operationId,
  () => {
    reviewed.value = false;
    confirmedAbsent.value = false;
    externalId.value = "";
  },
);
watch(
  () => props.ready,
  () => {
    reviewed.value = false;
  },
);
function attach(): void {
  emit("attach", externalId.value.trim());
}
const stages: Record<string, string> = {
  download: "Загрузка XML",
  store_file: "Сохранение файла",
  validation: "Проверка позиций",
  import: "Импорт позиций",
  download_images: "Загрузка изображений",
};
</script>
<template>
  <section class="flex min-w-0 flex-col gap-4" aria-label="Обновление Prom">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="text-base font-semibold">Обновление Prom</h3>
      <Button
        variant="ghost"
        size="sm"
        :disabled="busy"
        @click="emit('refresh')"
        >Перечитать результат</Button
      >
    </div>
    <p class="text-sm text-muted-foreground">
      Обновляются названия, описания на русском и украинском и галерея. При
      запуске формируется актуальный XML.
    </p>
    <FieldSet>
      <FieldLegend class="text-sm">Перед запуском</FieldLegend>
      <FieldGroup>
        <Field orientation="horizontal"
          ><Checkbox
            id="feed-reviewed"
            :model-value="reviewed"
            :disabled="busy || !ready"
            @update:model-value="reviewed = $event === true"
          /><FieldLabel for="feed-reviewed"
            >Я проверил preview сохранённого фида.</FieldLabel
          ></Field
        >
        <Field orientation="horizontal"
          ><Checkbox
            id="feed-force"
            :model-value="force"
            :disabled="busy"
            @update:model-value="force = $event === true"
          /><FieldLabel for="feed-force"
            >Принудительно обновить выбранные поля контента</FieldLabel
          ></Field
        >
        <FieldDescription
          >Принудительное обновление может перезаписать правки контента из
          кабинета Prom. Состав обновляемых полей остаётся
          ограниченным.</FieldDescription
        >
      </FieldGroup>
    </FieldSet>
    <div class="flex flex-wrap items-center gap-3">
      <Button
        :disabled="
          busy ||
          !ready ||
          !reviewed ||
          !enabled ||
          !verified ||
          !operation?.canStart
        "
        @click="emit('start', force)"
        >Обновить Prom</Button
      ><span v-if="!verified" class="text-sm text-muted-foreground"
        >Проверьте подключение Prom.</span
      ><span v-else-if="!enabled" class="text-sm text-muted-foreground"
        >Сначала включите выдачу фида.</span
      >
    </div>
    <template v-if="operation">
      <div class="grid min-w-0 gap-3 xl:grid-cols-3">
        <Card
          ><CardHeader
            ><CardTitle class="text-sm">Передача ссылки</CardTitle
            ><CardDescription>{{
              feedSubmissionLabel(operation)
            }}</CardDescription></CardHeader
          ><CardContent class="text-sm"
            >Запуск: {{ feedDate(operation.requestedAt) }}
            <p
              v-if="operation.manualResolution"
              class="mt-2 text-muted-foreground"
            >
              Результат уточнён вручную.
            </p></CardContent
          ></Card
        >
        <Card
          ><CardHeader
            ><CardTitle class="text-sm">Импорт Prom</CardTitle
            ><CardDescription>{{
              feedReportLabel(operation)
            }}</CardDescription></CardHeader
          ><CardContent class="flex flex-col gap-2 text-sm"
            ><p v-if="operation.externalId">
              ID импорта: <strong>{{ operation.externalId }}</strong>
            </p>
            <p>Проверка: {{ feedDate(operation.checkedAt) }}</p>
            <dl v-if="operation.report" class="grid grid-cols-2 gap-2">
              <dt>Всего</dt>
              <dd>{{ operation.report.total ?? "Нет данных" }}</dd>
              <dt>Обновлено</dt>
              <dd>{{ operation.report.updated ?? "Нет данных" }}</dd>
              <dt>Без изменений</dt>
              <dd>{{ operation.report.notChanged ?? "Нет данных" }}</dd>
              <dt>Создано</dt>
              <dd>{{ operation.report.created ?? "Нет данных" }}</dd>
              <dt>С ошибками</dt>
              <dd>{{ operation.report.withErrors ?? "Нет данных" }}</dd>
            </dl></CardContent
          ><CardFooter
            v-if="operation.report?.issues.length"
            class="flex-col items-start gap-1"
            ><p
              v-for="issue in operation.report.issues"
              :key="issue.stage"
              class="text-sm text-destructive"
            >
              Ошибка: {{ stages[issue.stage] ?? "Импорт" }}
            </p></CardFooter
          ></Card
        >
        <Card
          ><CardHeader
            ><CardTitle class="text-sm">Применение контента</CardTitle
            ><CardDescription>{{
              feedVerificationLabel(operation)
            }}</CardDescription></CardHeader
          ><CardContent class="text-sm text-muted-foreground"
            >Завершение импорта проверяется отдельно от совпадения полей
            публикаций. Галерея подтверждается только при надёжном
            совпадении.</CardContent
          ></Card
        >
      </div>
      <Alert v-if="operation.errorCode"
        ><AlertDescription>{{
          contentFeedIssue(operation.errorCode)
        }}</AlertDescription></Alert
      >
      <Alert v-if="operation.recoveryRequired"
        ><AlertDescription
          >Выполнение этапа прервалось. Можно восстановить безопасный шаг
          обработки.</AlertDescription
        ></Alert
      >
      <div v-if="operation.canResume" class="flex flex-wrap gap-2">
        <Button variant="outline" :disabled="busy" @click="emit('resume')"
          >Продолжить проверку</Button
        >
      </div>
      <Card v-if="operation.canAttach || operation.canResolve"
        ><CardHeader
          ><CardTitle class="text-sm">Выяснить результат передачи</CardTitle
          ><CardDescription
            >Найдите запуск в кабинете Prom. Привязка ID продолжит наблюдение за
            этим импортом.</CardDescription
          ></CardHeader
        ><CardContent class="flex flex-col gap-5">
          <form v-if="operation.canAttach" @submit.prevent="attach">
            <FieldGroup
              ><Field
                ><FieldLabel for="prom-import-id"
                  >ID импорта из кабинета Prom</FieldLabel
                ><Input
                  id="prom-import-id"
                  v-model="externalId"
                  inputmode="numeric"
                  pattern="[0-9]{1,19}"
                  required
                  :disabled="busy"
                /><FieldDescription
                  >ID можно привязать после появления итогового
                  отчёта.</FieldDescription
                ></Field
              >
              <div>
                <Button
                  type="submit"
                  variant="outline"
                  :disabled="busy || !externalId.trim()"
                  >Привязать и проверить</Button
                >
              </div></FieldGroup
            >
          </form>
          <FieldSet v-if="operation.canResolve"
            ><FieldLegend class="text-sm"
              >Ручное разрешение ситуации</FieldLegend
            ><FieldGroup
              ><Field orientation="horizontal"
                ><Checkbox
                  id="feed-confirm-absent"
                  :model-value="confirmedAbsent"
                  :disabled="busy"
                  @update:model-value="confirmedAbsent = $event === true"
                /><FieldLabel for="feed-confirm-absent"
                  >Я проверил в кабинете Prom, что этот импорт не был
                  запущен.</FieldLabel
                ></Field
              ><FieldDescription
                >После фиксации решения станет доступен новый ручной
                запуск.</FieldDescription
              >
              <div>
                <Button
                  variant="outline"
                  :disabled="busy || !confirmedAbsent"
                  @click="emit('resolve')"
                  >Зафиксировать решение</Button
                >
              </div></FieldGroup
            ></FieldSet
          >
        </CardContent></Card
      >
      <div
        v-for="item in operation.verification"
        :key="item.publicationId"
        class="rounded-lg border p-4"
      >
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <a
            :href="publicationLinks[item.publicationId]"
            class="text-sm font-medium underline underline-offset-4"
            >Публикация {{ item.externalId }}</a
          ><span class="text-xs text-muted-foreground"
            >Ключ импорта: {{ item.importKey }}</span
          >
        </div>
        <ul class="flex flex-col gap-2">
          <li
            v-for="field in item.fields"
            :key="field.field + field.locale"
            class="flex flex-wrap items-center justify-between gap-2 text-sm"
          >
            <span
              >{{ feedFieldLabel(field.field) }}
              {{ field.locale ? `(${field.locale})` : "" }}</span
            ><Badge variant="secondary">{{
              feedFieldStatus(field.status)
            }}</Badge>
          </li>
        </ul>
        <div
          v-if="item.observedGallery.length"
          class="mt-3 flex flex-wrap gap-3 text-sm"
        >
          <a
            v-for="(url, index) in item.observedGallery"
            :key="url"
            :href="url"
            target="_blank"
            rel="noopener noreferrer"
            class="underline underline-offset-4"
            >Фото {{ index + 1 }} в Prom</a
          >
        </div>
      </div>
    </template>
  </section>
</template>
