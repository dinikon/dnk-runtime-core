<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Button } from "@/components/ui/button";
import { X } from "@lucide/vue";
import { Spinner } from "@/components/ui/spinner";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogClose,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Stepper,
  StepperItem,
  StepperIndicator,
  StepperTitle,
} from "@/components/ui/stepper";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  CatalogImportDetails,
  ImportConfiguration,
  ImportRowsPage,
} from "../../model/import.types";
import CatalogImportSourceForm from "./CatalogImportSourceForm.vue";
import CatalogImportMappingForm from "./CatalogImportMappingForm.vue";
import CatalogImportProgress from "./CatalogImportProgress.vue";
import CatalogImportRows from "./CatalogImportRows.vue";
const props = defineProps<{
  open: boolean;
  existing: boolean;
  detail: CatalogImportDetails | undefined;
  draft: ImportConfiguration | null;
  dirty: boolean;
  loading: boolean;
  pending: boolean;
  sourcePending: boolean;
  error: string;
  rows: ImportRowsPage | undefined;
  rowsLoading: boolean;
  rowsError: string;
  rowPage: number;
  outcome: string;
}>();
defineEmits<{
  close: [];
  retry: [];
  source: [value: { file: File | null; url: string }];
  change: [value: ImportConfiguration];
  preview: [];
  start: [];
  cancel: [];
  resume: [];
  report: [];
  rowPage: [page: number];
  outcome: [outcome: string];
  rowsRetry: [];
  item: [id: string];
}>();
const editable = computed(
  () =>
    !!props.detail &&
    (["mapping", "preparing"].includes(props.detail.run.status) ||
      (props.detail.run.status === "failed" &&
        props.detail.run.total === 0 &&
        !!props.detail.analysis.format)),
);
const sourceReady = ref(false);
watch(
  () => props.open,
  (value) => {
    if (!value) sourceReady.value = false;
  },
);
const preparing = computed(() => props.detail?.run.status === "preparing");
const modeLabel = computed(
  () =>
    ({
      create: "Только создание",
      update: "Обновление по SKU",
      upsert: "Создание и обновление",
    })[props.draft?.mode ?? "create"],
);
const step = computed(() => (!props.detail ? 1 : editable.value ? 2 : 3));
</script>
<template>
  <Dialog
    :open="open"
    @update:open="
      (value) => {
        if (!value) $emit('close');
      }
    "
  >
    <DialogContent
      :show-close-button="false"
      class="flex h-dvh max-h-dvh max-w-full flex-col gap-0 overflow-hidden rounded-none p-0 sm:h-[90dvh] sm:max-h-[90dvh] sm:max-w-6xl sm:rounded-xl"
    >
      <DialogClose as-child
        ><Button
          variant="ghost"
          size="icon"
          class="absolute top-2 right-2 size-11 sm:top-3 sm:right-3"
          aria-label="Закрыть мастер"
          ><X /></Button
      ></DialogClose>
      <DialogHeader class="shrink-0 gap-1 px-5 pt-5 text-left sm:px-7 sm:pt-6"
        ><DialogTitle class="pr-8">Импорт позиций</DialogTitle
        ><DialogDescription class="truncate pr-8">{{
          detail?.run.name || "Перенесите товары из CSV или XML в Catalog"
        }}</DialogDescription></DialogHeader
      >
      <Stepper
        :model-value="step"
        aria-label="Шаги импорта"
        class="shrink-0 justify-between px-5 py-5 sm:px-7"
      >
        <StepperItem
          v-for="(label, index) in ['Источник', 'Поля', 'Импорт']"
          :key="label"
          :step="index + 1"
          class="flex-1 gap-2"
          ><StepperIndicator class="size-8 shrink-0">{{
            index + 1
          }}</StepperIndicator
          ><StepperTitle class="text-xs sm:text-sm">{{
            label
          }}</StepperTitle></StepperItem
        >
      </Stepper>
      <Separator />
      <div
        class="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 sm:px-7 sm:py-6"
      >
        <div class="flex min-w-0 flex-col gap-5">
          <div
            v-if="loading && !detail"
            class="flex flex-col gap-3"
            role="status"
          >
            <Skeleton class="h-12 w-full" /><Skeleton class="h-48 w-full" />
            <p class="text-sm text-muted-foreground">Загрузка импорта…</p>
          </div>
          <CatalogImportSourceForm
            v-else-if="!detail && !existing"
            form-id="catalog-import-source"
            :pending="sourcePending"
            @ready="sourceReady = $event"
            @submit="(value) => $emit('source', value)"
          />
          <template v-else-if="detail && editable">
            <Alert v-if="detail.run.error" variant="destructive"
              ><AlertTitle>Проверьте параметры источника</AlertTitle
              ><AlertDescription>{{
                detail.run.error
              }}</AlertDescription></Alert
            >
            <Alert v-if="detail.run.status === 'preparing'"
              ><AlertTitle>Подготовка предпросмотра</AlertTitle
              ><AlertDescription
                >Сохраняем источник и разбираем записи. Можно закрыть окно и
                вернуться через журнал.</AlertDescription
              ></Alert
            >
            <Alert v-if="detail.analysis.warnings.length"
              ><AlertTitle>Проверьте значения</AlertTitle
              ><AlertDescription
                ><ul class="list-disc pl-4">
                  <li
                    v-for="warning in detail.analysis.warnings"
                    :key="warning"
                  >
                    {{ warning }}
                  </li>
                </ul></AlertDescription
              ></Alert
            >
            <CatalogImportMappingForm
              v-if="draft && detail.analysis.format"
              :detail="detail"
              :value="draft"
              :pending="pending || detail.run.status === 'preparing'"
              :dirty="dirty"
              @change="(value) => $emit('change', value)"
            />
            <Skeleton v-else class="h-48 w-full" />
          </template>
          <template v-else-if="detail">
            <CatalogImportProgress :run="detail.run" :pending="pending" />
            <CatalogImportRows
              :data="rows"
              :loading="rowsLoading"
              :error="rowsError"
              :page="rowPage"
              :outcome="outcome"
              @page="(value) => $emit('rowPage', value)"
              @outcome="(value) => $emit('outcome', value)"
              @retry="$emit('rowsRetry')"
              @item="(value) => $emit('item', value)"
            />
          </template>
        </div>
      </div>
      <Separator />
      <footer
        aria-label="Действия импорта"
        class="shrink-0 bg-background px-5 pt-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-7 sm:pb-5"
      >
        <Alert
          v-if="error"
          variant="destructive"
          class="mb-3 max-h-28 overflow-y-auto"
          ><AlertTitle>Не удалось выполнить действие</AlertTitle
          ><AlertDescription
            >{{ error
            }}<Button
              v-if="existing && !detail"
              variant="outline"
              size="sm"
              @click="$emit('retry')"
              >Повторить</Button
            ></AlertDescription
          ></Alert
        >
        <template v-if="detail && editable">
          <p class="mb-3 text-xs text-muted-foreground" role="status">
            {{
              dirty
                ? "Есть изменения — обновите предпросмотр перед запуском."
                : `${modeLabel} · ${detail.run.total} записей`
            }}
          </p>
          <div class="grid grid-cols-2 gap-3 sm:flex sm:justify-end">
            <Button
              v-if="preparing"
              variant="outline"
              class="h-11 min-w-0 whitespace-normal"
              :disabled="pending"
              @click="$emit('cancel')"
              >Отменить подготовку</Button
            >
            <Button
              v-else
              variant="outline"
              class="h-11 min-w-0 whitespace-normal"
              :disabled="pending"
              @click="$emit('preview')"
              >Предпросмотр</Button
            >
            <Button
              class="h-11 min-w-0 whitespace-normal"
              :disabled="
                pending ||
                preparing ||
                dirty ||
                !draft?.mappings.length ||
                !detail.run.total ||
                detail.run.status !== 'mapping'
              "
              @click="$emit('start')"
              ><Spinner
                v-if="pending || preparing"
                data-icon="inline-start"
              />{{ preparing ? "Подготовка…" : "Запустить импорт" }}</Button
            >
          </div>
        </template>
        <div
          v-else-if="detail"
          class="grid grid-cols-[auto_minmax(0,1fr)] gap-3 sm:flex sm:justify-end"
        >
          <Button
            variant="outline"
            class="h-11 min-w-0 whitespace-normal"
            :disabled="pending"
            @click="$emit('report')"
            >Отчёт CSV</Button
          >
          <Button
            v-if="detail.run.canResume"
            class="h-11 min-w-0 whitespace-normal"
            :disabled="pending"
            @click="$emit('resume')"
            ><Spinner v-if="pending" data-icon="inline-start" />Продолжить
            импорт</Button
          >
          <Button
            v-else-if="
              ['queued', 'running', 'cancelling'].includes(detail.run.status)
            "
            class="h-11 min-w-0 whitespace-normal"
            :disabled="pending || detail.run.status === 'cancelling'"
            @click="$emit('cancel')"
            >{{
              detail.run.status === "cancelling"
                ? "Останавливаем…"
                : "Остановить импорт"
            }}</Button
          >
          <Button
            v-else
            class="h-11 min-w-0 whitespace-normal"
            @click="$emit('close')"
            >К журналу</Button
          >
        </div>
        <div v-else class="grid grid-cols-2 gap-3 sm:flex sm:justify-end">
          <Button
            variant="outline"
            class="h-11 min-w-0 whitespace-normal"
            @click="$emit('close')"
            >Закрыть</Button
          >
          <Button
            v-if="!existing"
            type="submit"
            form="catalog-import-source"
            class="h-11 min-w-0 whitespace-normal"
            :disabled="sourcePending || !sourceReady"
            ><Spinner v-if="sourcePending" data-icon="inline-start" />{{
              sourcePending ? "Загрузка…" : "Продолжить"
            }}</Button
          >
        </div>
      </footer>
    </DialogContent>
  </Dialog>
</template>
