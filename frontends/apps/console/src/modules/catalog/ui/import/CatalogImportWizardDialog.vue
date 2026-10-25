<script setup lang="ts">
import { computed } from "vue";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
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
      class="flex h-dvh max-h-dvh max-w-full flex-col gap-5 overflow-hidden rounded-none p-4 sm:h-auto sm:max-h-[90dvh] sm:max-w-6xl sm:rounded-lg sm:p-6"
    >
      <DialogHeader
        ><DialogTitle>Импорт позиций</DialogTitle
        ><DialogDescription>{{
          detail?.run.name || "Перенесите товары из CSV или XML в Catalog"
        }}</DialogDescription></DialogHeader
      >
      <Stepper
        :model-value="step"
        aria-label="Шаги импорта"
        class="shrink-0 justify-between border-b pb-4"
      >
        <StepperItem
          v-for="(label, index) in ['Источник', 'Сопоставление', 'Импорт']"
          :key="label"
          :step="index + 1"
          class="flex-1"
          ><StepperIndicator>{{ index + 1 }}</StepperIndicator
          ><StepperTitle class="text-xs sm:text-sm">{{
            label
          }}</StepperTitle></StepperItem
        >
      </Stepper>
      <div
        class="min-h-0 min-w-0 flex-1 overflow-y-auto overscroll-contain pr-1"
      >
        <div class="flex min-w-0 flex-col gap-5">
          <Alert v-if="error" variant="destructive"
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
            :pending="sourcePending"
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
              @preview="$emit('preview')"
              @start="$emit('start')"
            />
            <Skeleton v-else class="h-48 w-full" />
            <div class="flex justify-end">
              <Button
                variant="ghost"
                :disabled="pending"
                @click="$emit('cancel')"
                >Отменить подготовку</Button
              >
            </div>
          </template>
          <template v-else-if="detail">
            <CatalogImportProgress
              :run="detail.run"
              :pending="pending"
              @cancel="$emit('cancel')"
              @report="$emit('report')"
            />
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
      <div class="flex shrink-0 justify-end border-t pt-3">
        <Button variant="outline" @click="$emit('close')">{{
          step === 3 ? "Вернуться к журналу" : "Закрыть"
        }}</Button>
      </div>
    </DialogContent>
  </Dialog>
</template>
