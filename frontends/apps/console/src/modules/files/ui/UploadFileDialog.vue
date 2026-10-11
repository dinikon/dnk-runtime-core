<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Upload, X } from "@lucide/vue";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  bucketStatusLabels,
  formatStorageBytes,
  type StorageBucket,
} from "../model/types";
import {
  useUploadBatch,
  uploadStatusLabels,
  type UploadFileSubmit,
} from "../model/use-upload-batch";

const props = defineProps<{
  open: boolean;
  buckets: StorageBucket[];
  defaultBucketId?: string;
  busy: boolean;
  submit: UploadFileSubmit;
  refresh: () => Promise<void>;
}>();
const emit = defineEmits<{ close: []; busy: [value: boolean] }>();
const disk = ref("");
let trigger: HTMLElement | null = null;
watch(
  () => props.open,
  (open) => {
    if (open) trigger = document.activeElement as HTMLElement | null;
  },
  { flush: "sync" },
);
function restoreFocus(event: Event): void {
  event.preventDefault();
  if (trigger?.isConnected) trigger.focus();
}
const ready = computed(() =>
  props.buckets.filter((bucket) => bucket.status === "ready"),
);
const defaultDisk = computed(
  () =>
    ready.value.find((bucket) => bucket.id === props.defaultBucketId)?.id ??
    ready.value[0]?.id ??
    "",
);
const {
  items,
  running,
  stopped,
  refreshError,
  pendingCount,
  uploadedCount,
  totalBytes,
  uncertain,
  add,
  remove,
  stop,
  upload,
} = useUploadBatch(
  computed(() => props.open),
  props.submit,
  props.refresh,
);
const busy = computed(() => props.busy || running.value);
watch(running, (value) => emit("busy", value), { flush: "sync" });
watch(
  () => props.open,
  (open) => {
    if (open) disk.value = defaultDisk.value;
  },
);
watch(ready, (value) => {
  if (!disk.value && value.length) disk.value = defaultDisk.value;
});

function choose(files: FileList | null): void {
  if (!busy.value && files) add(Array.from(files));
}
function inputChanged(event: Event): void {
  const input = event.target as HTMLInputElement;
  choose(input.files);
  input.value = "";
}
function paste(event: ClipboardEvent): void {
  if (!event.clipboardData?.files.length) return;
  event.preventDefault();
  choose(event.clipboardData.files);
}
async function start(): Promise<void> {
  if (!busy.value && ready.value.some((bucket) => bucket.id === disk.value))
    await upload(disk.value);
}
</script>
<template>
  <Dialog :open="open" @update:open="!$event && !busy && emit('close')">
    <DialogContent
      lang="ru"
      class="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-2xl"
      :show-close-button="!busy"
      @escape-key-down="busy && $event.preventDefault()"
      @interact-outside="busy && $event.preventDefault()"
      @paste="paste"
      @close-auto-focus="restoreFocus"
    >
      <DialogHeader>
        <DialogTitle>Загрузить файлы</DialogTitle>
        <DialogDescription
          >Выберите несколько файлов и диск. Файлы загрузятся по очереди;
          одинаковые имена сохраняются отдельно.</DialogDescription
        >
      </DialogHeader>
      <form class="flex min-w-0 flex-col gap-5" @submit.prevent="start">
        <FieldGroup>
          <Field>
            <FieldLabel for="upload-disk">Диск</FieldLabel>
            <Select v-model="disk" :disabled="busy || !ready.length">
              <SelectTrigger id="upload-disk" class="w-full"
                ><SelectValue placeholder="Выберите диск"
              /></SelectTrigger>
              <SelectContent
                ><SelectGroup>
                  <SelectItem
                    v-for="bucket in buckets"
                    :key="bucket.id"
                    :value="bucket.id"
                    :disabled="bucket.status !== 'ready'"
                  >
                    {{ bucket.name
                    }}{{
                      bucket.status !== "ready"
                        ? ` · ${bucketStatusLabels[bucket.status]}`
                        : ""
                    }}
                  </SelectItem>
                </SelectGroup></SelectContent
              >
            </Select>
            <FieldDescription v-if="!ready.length"
              >Готовых дисков нет. Дождитесь подготовки
              хранилища.</FieldDescription
            >
          </Field>
          <Field>
            <FieldLabel for="upload-file">Файлы</FieldLabel>
            <div
              class="flex min-w-0 flex-col gap-3 rounded-lg border border-dashed bg-muted/30 p-4"
              @dragover.prevent
              @drop.prevent="choose($event.dataTransfer?.files ?? null)"
            >
              <Upload class="mx-auto size-7 text-muted-foreground" />
              <p class="text-center text-sm text-muted-foreground">
                Перетащите файлы, вставьте из буфера обмена или выберите их ниже
              </p>
              <!-- File input must stay uncontrolled: v-model cannot restore a filename. -->
              <input
                id="upload-file"
                type="file"
                multiple
                data-slot="input"
                class="file:text-foreground dark:bg-input/30 border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-sm shadow-xs outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:cursor-not-allowed disabled:opacity-50 focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]"
                :disabled="busy"
                aria-describedby="upload-help"
                @change="inputChanged"
              />
            </div>
            <FieldDescription id="upload-help"
              >До 1 ГиБ на каждый файл. Можно добавлять файлы к очереди
              несколькими выборами.</FieldDescription
            >
          </Field>
        </FieldGroup>
        <template v-if="items.length">
          <p
            class="text-sm text-muted-foreground"
            role="status"
            aria-live="polite"
          >
            Файлов: {{ items.length }} · {{ formatStorageBytes(totalBytes) }} ·
            Загружено: {{ uploadedCount }}
          </p>
          <ul class="flex min-w-0 flex-col gap-3" aria-label="Очередь загрузки">
            <li
              v-for="item in items"
              :key="item.id"
              class="flex min-w-0 flex-col gap-2 rounded-md border p-3"
            >
              <div class="flex min-w-0 items-start justify-between gap-2">
                <div class="min-w-0">
                  <p class="break-all text-sm font-medium">
                    {{ item.file.name }}
                  </p>
                  <p class="text-xs text-muted-foreground">
                    {{ formatStorageBytes(item.file.size) }}
                  </p>
                </div>
                <div class="flex shrink-0 items-center gap-1">
                  <Badge
                    :variant="
                      ['failed', 'invalid', 'uncertain'].includes(item.status)
                        ? 'destructive'
                        : 'secondary'
                    "
                    >{{ uploadStatusLabels[item.status] }}</Badge
                  >
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    :disabled="busy"
                    :aria-label="`Убрать из очереди: ${item.file.name}`"
                    @click="remove(item.id)"
                    ><X
                  /></Button>
                </div>
              </div>
              <div
                v-if="item.status === 'uploading'"
                class="flex flex-col gap-2"
                role="status"
                aria-live="polite"
              >
                <Progress
                  :model-value="item.progress"
                  :aria-label="`Передача: ${item.file.name}`"
                />
                <p class="text-xs text-muted-foreground">
                  {{
                    item.transferred
                      ? "Файл передан. Ожидаем сохранения на сервере…"
                      : `Передача файла: ${item.progress}%`
                  }}
                </p>
              </div>
              <p
                v-if="item.error"
                class="break-words text-sm text-destructive"
                role="alert"
              >
                {{ item.error }}
              </p>
              <Field
                v-if="item.status === 'uncertain'"
                orientation="horizontal"
              >
                <Checkbox
                  :id="`upload-retry-${item.id}`"
                  v-model="item.acknowledged"
                  :disabled="busy"
                />
                <FieldLabel :for="`upload-retry-${item.id}`"
                  >Я проверил список. Повторная загрузка создаст новый
                  файл.</FieldLabel
                >
              </Field>
            </li>
          </ul>
        </template>
        <Alert v-if="uncertain"
          ><AlertTitle>Проверьте результат загрузки</AlertTitle
          ><AlertDescription
            >Для файлов с неизвестным результатом проверьте список перед
            повтором. Остальные файлы очереди можно продолжить
            загружать.</AlertDescription
          ></Alert
        >
        <Alert v-if="refreshError" variant="destructive"
          ><AlertTitle>Список не обновлён</AlertTitle
          ><AlertDescription>{{ refreshError }}</AlertDescription></Alert
        >
        <Alert v-else-if="stopped"
          ><AlertTitle>Загрузка остановлена</AlertTitle
          ><AlertDescription
            >Оставшиеся файлы сохранены в очереди. Нажмите «Загрузить», чтобы
            продолжить.</AlertDescription
          ></Alert
        >
        <DialogFooter>
          <Button v-if="running" type="button" variant="outline" @click="stop"
            >Остановить после текущего</Button
          >
          <Button
            v-else
            type="button"
            variant="outline"
            :disabled="busy"
            @click="emit('close')"
            >Закрыть</Button
          >
          <Button
            type="submit"
            :disabled="
              busy ||
              !pendingCount ||
              !ready.some((bucket) => bucket.id === disk)
            "
            ><Spinner v-if="busy" /><Upload
              v-else
              data-icon="inline-start"
            />Загрузить<span v-if="pendingCount"
              >({{ pendingCount }})</span
            ></Button
          >
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
