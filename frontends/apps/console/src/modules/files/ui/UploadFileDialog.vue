<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { AxiosProgressEvent } from "axios";
import { Upload } from "@lucide/vue";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  FieldGroup,
  Field,
  FieldLabel,
  FieldDescription,
  FieldError,
} from "@/components/ui/field";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { getApiErrorStatus } from "@/app/providers/http";
import { fileError } from "../model/errors";
import {
  bucketStatusLabels,
  formatStorageBytes,
  type StorageBucket,
} from "../model/types";
const props = defineProps<{
  open: boolean;
  buckets: StorageBucket[];
  busy: boolean;
  submit: (
    file: File,
    bucketId: string,
    progress: (event: AxiosProgressEvent) => void,
  ) => Promise<void>;
  refresh: () => Promise<void>;
}>();
const emit = defineEmits<{ close: [] }>();
const file = ref<File | null>(null);
const disk = ref("");
const error = ref("");
const progress = ref(0);
const transferred = ref(false);
const ambiguous = ref(false);
const acknowledged = ref(false);
const ready = computed(() =>
  props.buckets.filter((bucket) => bucket.status === "ready"),
);
watch(
  () => props.open,
  (open) => {
    if (open) {
      file.value = null;
      error.value = "";
      ambiguous.value = false;
      acknowledged.value = false;
      progress.value = 0;
      transferred.value = false;
      disk.value = ready.value[0]?.id ?? "";
    }
  },
);
watch(ready, (items) => {
  if (!disk.value && items.length) disk.value = items[0]!.id;
});
function choose(files: FileList | null): void {
  if (props.busy) return;
  if (files?.length !== 1) {
    error.value = "Выберите один файл.";
    return;
  }
  file.value = files[0] ?? null;
  if (!ambiguous.value) error.value = "";
}
async function upload(): Promise<void> {
  if (
    props.busy ||
    !file.value ||
    !ready.value.some((item) => item.id === disk.value) ||
    (ambiguous.value && !acknowledged.value)
  )
    return;
  error.value = "";
  progress.value = 0;
  transferred.value = false;
  try {
    await props.submit(file.value, disk.value, (event) => {
      const total = event.total;
      if (total)
        progress.value = Math.min(
          100,
          Math.round((event.loaded / total) * 100),
        );
      transferred.value = !!total && event.loaded >= total;
    });
    emit("close");
  } catch (cause) {
    error.value = fileError(cause);
    const status = getApiErrorStatus(cause);
    ambiguous.value = status === null || status === 408 || status >= 500;
    acknowledged.value = false;
    if (ambiguous.value) {
      try {
        await props.refresh();
      } catch {
        /* The list displays its own refresh error. */
      }
    }
  }
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !busy && emit('close')"
    ><DialogContent
      class="max-h-[calc(100svh-2rem)] overflow-y-auto"
      :show-close-button="!busy"
      @escape-key-down="busy && $event.preventDefault()"
      @interact-outside="busy && $event.preventDefault()"
      ><DialogHeader
        ><DialogTitle>Загрузить файл</DialogTitle
        ><DialogDescription
          >Выберите файл и готовый диск. Одинаковые имена сохраняются как
          отдельные файлы.</DialogDescription
        ></DialogHeader
      >
      <form class="flex min-w-0 flex-col gap-5" @submit.prevent="upload">
        <FieldGroup
          ><Field
            ><FieldLabel for="upload-disk">Диск</FieldLabel
            ><Select v-model="disk" :disabled="busy || !ready.length"
              ><SelectTrigger id="upload-disk" class="w-full"
                ><SelectValue placeholder="Выберите диск" /></SelectTrigger
              ><SelectContent
                ><SelectGroup
                  ><SelectItem
                    v-for="bucket in buckets"
                    :key="bucket.id"
                    :value="bucket.id"
                    :disabled="bucket.status !== 'ready'"
                    >{{ bucket.name
                    }}{{
                      bucket.status !== "ready"
                        ? ` · ${bucketStatusLabels[bucket.status]}`
                        : ""
                    }}</SelectItem
                  ></SelectGroup
                ></SelectContent
              ></Select
            ><FieldDescription v-if="!ready.length"
              >Готовых дисков нет. Дождитесь подготовки
              хранилища.</FieldDescription
            ></Field
          >
          <Field :data-invalid="!!error"
            ><FieldLabel for="upload-file">Файл</FieldLabel>
            <div
              class="flex min-w-0 flex-col gap-3 rounded-lg border border-dashed bg-muted/30 p-4"
              @dragover.prevent
              @drop.prevent="choose($event.dataTransfer?.files ?? null)"
            >
              <Upload class="mx-auto size-7 text-muted-foreground" />
              <p class="text-center text-sm text-muted-foreground">
                Перетащите один файл или выберите его ниже
              </p>
              <Input
                id="upload-file"
                type="file"
                :disabled="busy"
                :aria-invalid="!!error"
                :aria-describedby="error ? 'upload-error' : 'upload-help'"
                @change="choose(($event.target as HTMLInputElement).files)"
              />
              <p v-if="file" class="break-all text-sm font-medium">
                {{ file.name }} · {{ formatStorageBytes(file.size) }}
              </p>
            </div>
            <FieldDescription id="upload-help"
              >Максимальный размер определяется настройками сервера. По
              умолчанию — 100 МиБ.</FieldDescription
            ><FieldError v-if="error" id="upload-error">{{
              error
            }}</FieldError></Field
          ></FieldGroup
        >
        <div
          v-if="busy"
          class="flex flex-col gap-2"
          role="status"
          aria-live="polite"
        >
          <Progress :model-value="progress" aria-label="Передача файла" />
          <p class="text-sm text-muted-foreground">
            {{
              transferred
                ? "Файл передан. Ожидаем сохранения на сервере…"
                : `Передача файла: ${progress}%`
            }}
          </p>
        </div>
        <Alert v-if="ambiguous"
          ><AlertTitle>Ответ сервера не получен</AlertTitle
          ><AlertDescription
            >Список обновлён: проверьте, появился ли файл, прежде чем повторять
            загрузку. Если обновление не удалось, используйте кнопку «Обновить»
            после закрытия формы.</AlertDescription
          ></Alert
        >
        <Field v-if="ambiguous" orientation="horizontal"
          ><Checkbox
            id="upload-retry"
            v-model="acknowledged"
            :disabled="busy"
          /><FieldLabel for="upload-retry" class="font-normal"
            >Я проверил список. Повторная загрузка создаст новый
            файл.</FieldLabel
          ></Field
        >
        <DialogFooter
          ><Button
            type="button"
            variant="outline"
            :disabled="busy"
            @click="emit('close')"
            >Отмена</Button
          ><Button
            type="submit"
            :disabled="
              busy ||
              !file ||
              !ready.some((item) => item.id === disk) ||
              (ambiguous && !acknowledged)
            "
            ><Spinner v-if="busy" /><Upload
              v-else
              data-icon="inline-start"
            />Загрузить</Button
          ></DialogFooter
        >
      </form>
    </DialogContent></Dialog
  >
</template>
